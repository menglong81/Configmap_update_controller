# Hot update controller

监听k8s configmap变化事件关联应用到该configmap的pod进行相关操作


## 项目背景

configmap更新触发业务热加载

## 原理
configmap env形式注入变量容器内部是无法进行重载的  
挂载Volume形式则相关pod 10s后会又kubelet进行周期性检测和更新  
当监听到configmap更新事件后和pod内挂载的文件进行比对  
如果pod的volume已经被kubelet更新则触发业务热更新  
## 如何使用

定义annotations 
reloader/check|reloader/command
```
apiVersion: v1
kind: Pod
metadata:
  labels:
    name: busybox
    role: master
  name: busybox
  annotations:
    reloader/command: '你可以设置你要触发的操作'
```

```
日志输出
####################################################################################################
2020-12-23 23:28:01,290 controler wait_and_reload INFO    : Reload in busybox succeeded
2020-12-23 23:28:35,172 controler watch INFO    : Event: MODIFIED cmtest in namespace default
####################################################################################################
```