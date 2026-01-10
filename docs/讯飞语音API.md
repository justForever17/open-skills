讯飞开放平台 - 实时语音听写 API 的首页及注册申请全流程：
一、实时语音听写 API 首页
直接访问讯飞开放平台对应服务页：首页链接：<https://www.xfyun.cn/services/voicedictation（页面包含服务介绍、支持语言> / 格式、接入文档等信息）
二、注册申请全流程指南
步骤 1：注册开发者账号
打开讯飞开放平台官网（<https://www.xfyun.cn），点击右上角「登录> / 注册」→「立即注册」；
填写手机号 + 验证码，设置登录密码（8 位以上，含大小写 + 数字）；
完成注册后直接登录系统。
步骤 2：创建应用并开通服务
登录后进入「控制台」→「我的应用」→「创建新应用」；
填写应用信息：
应用名称（如 “我的语音听写工具”）；
应用类型（选 Web/Android/iOS 等，按需选择）；
应用描述（选填）；
提交后，在应用详情页的「服务列表」中，找到「语音听写（流式版）」并点击「开通」（免费服务，无额外费用）。
步骤 3：获取 API 凭证
开通服务后，在应用的「服务管理页」中，即可查看：
AppID：应用唯一标识；
API Key + API Secret：接口调用的鉴权密钥（需妥善保存，不要泄露）。
步骤 4：完成实名认证（可选）
若仅测试使用，可暂不认证；
若需正式商用，进入「账户中心」→「实名认证」，上传身份证 / 企业资质，提交审核（1-2 个工作日通过）。
步骤 5：接入 API（测试）
参考官网文档（<https://www.xfyun.cn/doc/asr/voicedictation/API.html），选择> HTTP/WebSocket 方式调用；
平台提供 Python/Java 等语言的 Demo 代码，直接替换凭证即可快速测试。

# 讯飞实时语音听写API（流式版）详细调用步骤

本指南基于 **WebSocket协议**（推荐实时场景），以Python为例，涵盖**环境准备→鉴权签名→音频处理→接口调用→结果解析**全流程，适配你的 `v8chat` 项目集成需求。

## 前提条件

1. 已完成讯飞开放平台注册，创建应用并开通「语音听写（流式版）」服务，获取3个核心凭证：
    - `APPID`：应用唯一标识
    - `APISecret`：鉴权密钥
    - `APIKey`：鉴权密钥
2. 音频格式要求（必须满足）：
    - 编码：**PCM 16bit**（无压缩）
    - 采样率：16000Hz（推荐）/8000Hz
    - 声道：**单声道**
    - 单次音频时长：≤60秒

## 整体流程概览

```
准备环境 → 生成鉴权签名 → 音频预处理 → 建立WebSocket连接 → 分片发送音频 → 接收并解析结果 → 关闭连接
```

## 步骤1：环境准备

### 1.1 安装依赖库

Python需安装WebSocket客户端和加密相关库，执行命令：

```bash
pip install websocket-client requests pycryptodome
```

### 1.2 音频预处理（关键！格式必须符合要求）

如果你的音频是 `MP3/WAV` 等格式，需转换为 **PCM 16k 单声道**，推荐使用 `ffmpeg` 工具：

#### 安装ffmpeg

- Windows：下载[ffmpeg官网](https://ffmpeg.org/)包，配置环境变量
- Mac：`brew install ffmpeg`
- Linux：`sudo apt install ffmpeg`

#### 转换命令

```bash
# 将MP3转换为PCM 16k 单声道 （输出文件为raw格式，无头部信息）
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f s16le output.pcm
```

## 步骤2：生成鉴权签名（核心！接口调用的通行证）

讯飞API采用 `HMAC-SHA256` 签名机制，需通过 `APIKey`、`APISecret` 生成 `authorization` 签名，步骤如下：

### 2.1 签名计算逻辑

1. 拼接待签名字符串 `signature_origin`，格式为：

    ```
    host: iat.xf-yun.com
    date: 当前UTC时间（RFC1123格式，如 Tue, 14 May 2024 08:46:48 GMT）
    GET /v1/iat HTTP/1.1
    ```

2. 使用 `APISecret` 作为密钥，对 `signature_origin` 进行 `HMAC-SHA256` 加密，再进行Base64编码，得到 `signature`。
3. 拼接最终 `authorization` 字符串：

    ```
    authorization: api_key="你的APIKey", algorithm="hmac-sha256", headers="host date request-line", signature="步骤2生成的signature"
    ```

### 2.2 Python代码实现签名生成

```python
import time
import base64
import hmac
from hashlib import sha256
from datetime import datetime

def generate_auth_header(api_key, api_secret):
    # 1. 构建请求相关参数
    host = "iat.xf-yun.com"
    request_uri = "/v1/iat"
    method = "GET"
    
    # 2. 获取UTC时间（RFC1123格式）
    now = datetime.utcnow()
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # 3. 拼接待签名字符串
    signature_origin = f"host: {host}\ndate: {date}\n{method} {request_uri} HTTP/1.1"
    
    # 4. HMAC-SHA256加密 + Base64编码
    signature = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), 
                 signature_origin.encode('utf-8'), 
                 digestmod=sha256).digest()
    ).decode('utf-8')
    
    # 5. 拼接Authorization头
    authorization = (
        f'api_key="{api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    
    return authorization, date, host
```

## 步骤3：建立WebSocket连接并调用接口

### 3.1 核心调用逻辑

1. 拼接WebSocket请求URL，包含 `APPID`、`authorization` 等参数
2. 建立WebSocket连接
3. **分片发送PCM音频数据**（推荐每片20ms，对应640字节，避免单次发送过大）
4. 实时接收服务端返回的转写结果
5. 发送结束标识，关闭连接

### 3.2 完整Python调用代码

```python
import websocket
import json
import threading

# 替换为你的凭证
APPID = "你的APPID"
APIKey = "你的APIKey"
APISecret = "你的APISecret"
PCM_FILE_PATH = "output.pcm"  # 步骤1生成的PCM文件

# 全局变量：存储最终转写结果
final_result = ""

# 接收消息的回调函数
def on_message(ws, message):
    global final_result
    data = json.loads(message)
    # 解析结果（流式返回，需拼接）
    if data["code"] == 0:
        # result字段是转写核心数据
        result = data["data"]["result"]["ws"]
        for w in result:
            final_result += "".join([cw["w"] for cw in w["cw"]])
        print(f"实时转写结果：{final_result}")
    else:
        print(f"调用失败：{data['message']}")

# 连接关闭的回调函数
def on_close(ws, close_status_code, close_msg):
    print(f"连接关闭，最终转写结果：{final_result}")

# 分片发送音频数据
def send_audio(ws, pcm_path):
    chunk_size = 640  # 20ms 16k 单声道 PCM数据大小
    with open(pcm_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)  # 二进制发送音频
            # 模拟实时说话间隔
            threading.Event().wait(0.02)
    # 发送结束标识（必须！否则服务端不会返回最终结果）
    end_frame = {
        "end": True
    }
    ws.send(json.dumps(end_frame))

if __name__ == "__main__":
    # 1. 生成鉴权头
    authorization, date, host = generate_auth_header(APIKey, APISecret)
    
    # 2. 拼接WebSocket URL
    ws_url = (
        f"wss://iat.xf-yun.com/v1/iat?appid={APPID}"
        f"&authorization={authorization}"
        f"&date={date}"
        f"&host={host}"
    )
    
    # 3. 配置WebSocket
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_close=on_close
    )
    
    # 4. 启动线程发送音频
    threading.Thread(target=send_audio, args=(ws, PCM_FILE_PATH)).start()
    
    # 5. 保持连接
    ws.run_forever()
```

## 步骤4：响应结果解析

### 4.1 成功响应JSON结构

```json
{
  "code": 0,        // 0=成功，非0=失败
  "message": "success",
  "sid": "xxxx",    // 会话ID
  "data": {
    "result": {
      "ws": [       // 词级结果列表
        {
          "cw": [   // 字级结果列表
            {"w": "你", "sc": 0},
            {"w": "好", "sc": 0}
          ]
        }
      ],
      "ls": false   // 是否最后一片结果
    },
    "status": 2     // 1=开始，2=中间，3=结束
  }
}
```

### 4.2 错误码排查（常见问题）

| 错误码 | 原因 | 解决方案 |
|--------|------|----------|
| 10105 | 鉴权失败 | 检查APPID/APIKey/APISecret是否正确；检查签名时间是否为UTC时间 |
| 10300 | 音频时长超限 | 单次音频≤60秒，分片发送时控制总时长 |
| 10301 | 音频格式错误 | 确保是PCM 16k 单声道，无头部信息 |

## 步骤5：项目集成建议（适配v8chat）

1. **前端采集音频**：使用 `MediaRecorder` API采集用户语音，转换为PCM格式后通过WebSocket发送到FastAPI后端。
2. **后端转发处理**：FastAPI作为中间层，接收前端音频数据，调用讯飞API并实时返回转写结果。
3. **Docker部署**：将依赖和配置打包进Docker镜像，设置环境变量存储 `APPID/APIKey/APISecret`，避免硬编码。

## 注意事项

1. 免费版接口**并发量有限**，商用需联系讯飞升级套餐。
2. 签名有效期为 **5分钟**，建议每次调用前重新生成签名。
3. 流式传输时，音频分片间隔建议 **20ms**，过大会导致实时性下降。
