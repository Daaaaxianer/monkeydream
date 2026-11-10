---
{
  "title": "OpenCloudOS 9 安装 Docker：提示不支持发行版后的处理记录",
  "slug": "opencloudos9-install-docker",
  "summary": "OpenCloudOS 9 安装 Docker 时提示不支持当前发行版，改为手动添加 Docker CentOS 仓库后安装成功。记录安装步骤、验证方法和几个容易混淆的问题。",
  "date": "2026-11-10",
  "updated": "2026-11-10",
  "article_type": "note",
  "evidence_status": "unspecified",
  "category": "技术分享",
  "category_slug": "tech",
  "tags": [
    {"name": "OpenCloudOS", "slug": "opencloudos"},
    {"name": "Docker", "slug": "docker"},
    {"name": "Linux", "slug": "linux"}
  ],
  "sessions": [],
  "code_url": "",
  "data_url": "",
  "draft": false
}
---

## 遇到的问题

这次在 OpenCloudOS 9 上安装 Docker，安装过程提示没有对应的发行版。后来参考[腾讯云开发者社区的这篇文章](https://cloud.tencent.com/developer/article/2505114)，手动添加 Docker 的 CentOS 仓库，再通过 DNF 安装，就正常了。把处理过程记下来，方便以后重装时查。

当时的完整报错、安装入口和 Docker 版本没有留存，因此这里只记录现象和成功的处理方法，不把下面的示例写成当时的终端输出。

## 为什么换一种安装方式就能继续

如果用的是 Docker 一键安装脚本，它会先读取系统信息，再选择对应的安装流程。脚本没有识别到当前发行版时，可能在这一步退出。[Docker 安装脚本源码](https://github.com/docker/docker-install/blob/master/install.sh)可以用来核对这类判断逻辑。

这次改成手动添加软件仓库，直接交给 DNF 安装，绕开了安装入口对发行版的自动识别。由于没有保留原始日志，还不能确认当时具体停在哪个判断分支。

下面使用的是 **Docker 为 CentOS 提供的仓库**。本文记录的是它在这次 OpenCloudOS 9 环境中安装成功的做法，不能据此推断所有 OpenCloudOS 9 小版本和硬件架构都适用。Docker 的[官方 CentOS 安装文档](https://docs.docker.com/engine/install/centos/)列出的支持系统也需要与本机情况分开看。

## 安装步骤

以下命令在 OpenCloudOS 9 主机上执行。普通用户使用 `sudo`；已经以 root 登录时可以省略。

### 1. 查看系统信息

建议先记下系统版本和架构，后续排错时用得上：

```bash
cat /etc/os-release
uname -m
```

### 2. 按需移除旧版软件包

参考步骤先清理可能冲突的旧包：

```bash
sudo dnf remove docker docker-client docker-common docker-selinux
```

如果提示这些包没有安装，可以继续。已有容器业务的机器先查看 DNF 列出的移除清单，确认影响后再执行。

### 3. 添加 Docker 仓库

先安装仓库管理插件，避免遇到找不到 `config-manager` 的情况：

```bash
sudo dnf install dnf-plugins-core
```

添加仓库并查看是否生效：

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf repolist
```

检查列表中是否有 `docker-ce-stable`。这里的地址是 Docker 官方的 CentOS 软件源，不是 OpenCloudOS 自带的软件源。

### 4. 安装 Docker

这次采用的基础安装命令是：

```bash
sudo dnf install docker-ce docker-ce-cli containerd.io
```

其中 `docker-ce` 是容器引擎，`docker-ce-cli` 是命令行工具，`containerd.io` 提供容器运行时。

如果后续需要构建镜像或使用 Compose，可以另装插件；这属于补充用法，不是本次安装成功所必需的步骤：

```bash
sudo dnf install docker-buildx-plugin docker-compose-plugin
```

### 5. 启动并设置开机自启

```bash
sudo systemctl enable --now docker
```

`--now` 会立即启动服务，`enable` 则让服务随系统启动。

## 安装后怎么确认

下面是补充的检查方法，本文没有保存这些命令的实测输出：

```bash
systemctl is-active docker
sudo docker version
sudo docker info
sudo docker run --rm hello-world
```

服务状态应为 `active`；`docker version` 应能显示 Client 和 Server 信息。`hello-world` 用来检查镜像拉取和容器运行，正常执行后会输出确认消息并退出。

如果前面几项正常，只有拉取镜像超时，先排查访问镜像仓库的网络问题。软件包安装成功与镜像下载成功是两件事。

## 再遇到报错时先看哪里

| 现象 | 先检查什么 |
| --- | --- |
| 提示不支持当前发行版 | 确认是否由一键安装入口报出，再尝试本文的仓库安装方式 |
| 找不到 `config-manager` | 是否安装了 `dnf-plugins-core` |
| 找不到 `docker-ce` 软件包 | `dnf repolist` 中是否有 Docker 仓库，仓库元数据是否下载成功 |
| 仓库地址返回 404 | 核对仓库地址实际使用的版本路径和本机架构，不能只凭“添加成功”判断可用 |
| 无法连接 Docker daemon | 检查 Docker 服务状态和启动日志 |
| 普通用户执行 Docker 提示权限不足 | 先用 `sudo docker ...` 检查 |

查看服务状态和日志：

```bash
sudo systemctl status docker --no-pager
sudo journalctl -u docker -n 100 --no-pager
```

仓库已配置但软件包仍搜不到时，可以刷新元数据再查：

```bash
sudo dnf makecache --refresh
dnf list docker-ce --showduplicates
```

如果仍有依赖冲突，保留完整输出再处理，不要直接跳过依赖检查或关闭 GPG 校验。

## 补充：在容器里运行 OpenCloudOS 9

参考截图还提到了带 systemd 的 OpenCloudOS 容器。这是在 Docker 已装好之后的另一种用途，不需要为了安装 Docker 而先运行它。

如果确实需要在容器中测试 systemd 或多个服务，可以参考 [OpenCloudOS 容器镜像文档](https://docs.opencloudos.org/OCS/Install_Guide/ocs-docker/)及对应的 [init 镜像标签](https://hub.docker.com/r/opencloudos/opencloudos9-init/tags)，选择可用标签。截图给出的命令是：

```bash
sudo docker run --privileged -it opencloudos/opencloudos9-init /sbin/init
```

这条命令未在本次记录中验证。`--privileged` 会放大容器权限，仅在需要并信任镜像的测试环境中使用；普通应用容器通常不需要这个选项。

## 仓库的后续管理

如果以后需要暂时禁用 Docker 软件源，可以执行：

```bash
sudo dnf config-manager --set-disabled docker-ce-stable
```

这会影响后续从该源安装和更新软件包，不会停止正在运行的 Docker。需要恢复时执行：

```bash
sudo dnf config-manager --set-enabled docker-ce-stable
```

## 参考资料

- [OpenCloudOS9 快速安装 Docker（详解）](https://cloud.tencent.com/developer/article/2505114)：本次安装成功所参考的处理方法。本文结合自己的问题重新整理，并非原文转载。
- [Docker Engine：CentOS 安装文档](https://docs.docker.com/engine/install/centos/)：仓库、软件包和验证命令的官方说明。
- [Docker 一键安装脚本源码](https://github.com/docker/docker-install/blob/master/install.sh)：发行版识别逻辑。
- [OpenCloudOS 容器镜像使用指南](https://docs.opencloudos.org/OCS/Install_Guide/ocs-docker/)：容器镜像与 init 镜像的补充资料。

本次确认的结果是：OpenCloudOS 9 安装时提示没有对应发行版，改用上述仓库安装方法后正常。具体小版本、架构和 Docker 版本未留存，后续重装时应补记这些信息。
