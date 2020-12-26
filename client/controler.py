#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# file:controler.py
# author: menglong.zhou@qunar.com
# 2020/12/23 9:46 PM

import kubernetes as k8s
import json
import threading
import sys
import os
import time
import hashlib
import traceback
from common.log import MAIN_LOG
from common.mq import Q


class Kube(object):

    account_dir = '/var/run/secrets/kubernetes.io/serviceaccount'
    api_server = os.getenv(
        "api_server",
        "https://kubernetes.default.svc.cluster.local")
    namespace = 'default'

    def __init__(self):
        try:
            self.q = Q()
            k8s.config.load_kube_config(
                'conf/kubeconfig')  # load local kubeconfig
            self.v1 = k8s.client.CoreV1Api()
        except k8s.config.config_exception.ConfigException:
            with open(f'{Kube.account_dir}/token', 'r') as f:  # use mounted serviceaccount token
                token = f.__next__().strip()
            configuration = k8s.client.Configuration()
            configuration.ssl_ca_cert = f'{Kube.account_dir}/ca.crt'
            configuration.api_key['authorization'] = token
            configuration.api_key_prefix['authorization'] = 'Bearer'
            configuration.host = Kube.api_server
            self.v1 = k8s.client.CoreV1Api(k8s.client.ApiClient(configuration))

        # self.q = Q()

    def watch(self):
        '''
        监听k8s事件 过滤type是MODIFIED类型
        按照configmap取到关联的pod
        放入到reload 队列
        '''
        w = k8s.watch.Watch()
        for event in w.stream(self.v1.list_config_map_for_all_namespaces):
            try:
                namespace = event['object'].metadata.namespace
                if event['type'] == 'MODIFIED':
                    MAIN_LOG.logger.info(
                        f"Event: {event['type']} {event['object'].metadata.name} in namespace {namespace}")
                    pods_to_reload = self.find_pods_with_configmap(
                        cm=event['object'], namespace=namespace)
                    if pods_to_reload:
                        for i in pods_to_reload:
                            p, c, mp = i
                            self.q.put({
                                'configmap': event['object'],
                                'pod': p,
                                'container': c,
                                'mountpath': mp,
                                'namespace': namespace

                            })
            except Exception as e:
                MAIN_LOG.logger.error(traceback.format_exc())

    def touch_annotation(self, pod, namespace=namespace):

        def update_time(): return int(round(time.time() * 1000))
        pod.metadata.annotations['reloader/updated'] = str(update_time())
        # pod.metadata.resourceVersion = str(update_time())
        self.v1.patch_namespaced_pod(
            name=pod.metadata.name,
            namespace=namespace,
            body=pod)
        MAIN_LOG.logger.info(f'touched annotation on {pod.metadata.name}')

    def wait_and_reload(self, cm, pod, container, mountpath, namespace):
        while not self.comparemd5(cm, pod, container, mountpath, namespace):
            MAIN_LOG.logger.info(pod.metadata.name, 'waiting')
            time.sleep(2)

        if 'reloader/check' in pod.metadata.annotations:
            check_result = self.exec_command_in_pod(pod, container, pod.metadata.annotations['reloader/check'],
                                                    namespace=namespace)
            if check_result[3]["status"] == 'Success':
                MAIN_LOG.logger.info(
                    f'Config check in {pod.metadata.name} succeeded')
            else:
                MAIN_LOG.logger.error(f'Config check in {pod.metadata.name} failed:\n {check_result[3]["message"]}\n '
                                      f"stderr: {check_result[2]}")
                return None
        command = pod.metadata.annotations['reloader/command']
        reload_result = self.exec_command_in_pod(
            pod, container, command, namespace=namespace)

        if reload_result[3]["status"] == 'Success':
            MAIN_LOG.logger.info(f'Reload in {pod.metadata.name} succeeded')
        else:
            MAIN_LOG.logger.error(f'Reload check in {pod.metadata.name} failed:\n {reload_result[3]["message"]}\n '
                                  f"stderr: {reload_result[2]}")

    def find_pods_with_configmap(self, cm, namespace=namespace):
        res = []
        for p in [pod for pod in self.v1.list_namespaced_pod(namespace).items if pod.metadata.annotations and
                  'reloader/command' in pod.metadata.annotations]:
            for v in p.spec.volumes:
                try:
                    if hasattr(
                            v, 'config_map') and v.config_map.name == cm.metadata.name:
                        for c in p.spec.containers:
                            for vm in c.volume_mounts:
                                if vm.name == v.name:
                                    res.append((p, c.name, vm.mount_path))
                except AttributeError as err:
                    pass
        return res

    def comparemd5(self, cm, pod, container, mountpath, namespace):
        '''
        比较md5类型 kubelet每10s更新一次pods 按照MD5来判断volume是否已更新
        :param cm:
        :param pod:
        :param container:
        :param mountpath:
        :param namespace:
        :return:
        '''
        cm_hashes = {
            file: hashlib.md5(
                cm.data[file].encode()).hexdigest() for file in cm.data}
        pod_hashes = {file: self.exec_command_in_pod(pod, container,
                                                     f'md5sum {mountpath}/{file}', namespace=namespace)[1].split()[0] for
                      file in cm_hashes}
        # MAIN_LOG.info(cm_hashes, pod_hashes)
        return cm_hashes == pod_hashes

    def exec_command_in_pod(self, pod, container, command,
                            namespace=namespace, shell="/bin/sh"):
        client = k8s.stream.stream(self.v1.connect_get_namespaced_pod_exec,
                                   pod.metadata.name,
                                   namespace,
                                   command=[shell, '-c', command],
                                   container=container,
                                   stderr=True, stdin=False,
                                   stdout=True, tty=False, _preload_content=False)
        client.run_forever(timeout=60)
        return [client.read_channel(i) for i in range(
            3)] + [json.loads(client.read_channel(3))]

    @staticmethod
    def api():
        Kube().watch()


class Handle(object):

    def __init__(self):
        self.k = Kube()

    def handle_event(self):
        while True:
            message = self.k.q.get()
            if not message:
                continue
            self.k.touch_annotation(
                pod=message.get('pod'),
                namespace=message.get('namespace'))
            self.k.wait_and_reload(
                cm=message.get('configmap'),
                pod=message.get('pod'),
                container=message.get('container'),
                mountpath=message.get('mountpath'),
                namespace=message.get('namespace'))

    @staticmethod
    def api():
        Handle().handle_event()


def run():
    t = list()
    for i in range(5):
        t.append(threading.Thread(target=Handle.api, ))
    t.append(threading.Thread(target=Kube.api, ))
    try:
        for i in t:
            i.start()
        while True:
            for i in t:
                i.join(1)
                # if not i.isAlive:  #before python3.9
                if not i.is_alive():
                    break
    except KeyboardInterrupt:
        print("Ctrl-c pressed ...")
        sys.exit(1)


if __name__ == '__main__':
    run()
