# 洛克王国自动激活工具

自动获取洛克王国每日公告中的资格码并进行兑换的工具。

## 功能特性

- ✅ 多线程高频请求公告列表,提高成功率
- ✅ 自动提取公告中的资格口令
- ✅ 支持OCR自动识别验证码或手动输入
- ✅ GUI图形化界面,配置简单
- ✅ 按日期保存日志
- ✅ 配置持久化保存

## 目录结构

```
luoke/
├── src/                    # 源代码目录
│   ├── config_manager.py   # 配置管理模块
│   ├── logger.py           # 日志管理模块
│   ├── api_client.py       # HTTP接口封装
│   ├── announcement_fetcher.py  # 多线程公告获取
│   ├── password_extractor.py    # 口令提取模块
│   ├── captcha_handler.py       # 验证码处理模块
│   ├── redeemer.py              # 兑换控制器
│   └── gui.py                   # GUI界面
├── main.py                 # 程序入口
├── config.json             # 配置文件(首次运行自动生成)
├── logs/                   # 日志目录(自动生成)
├── requirements.txt        # 依赖列表
└── README.md               # 说明文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖说明

- `requests`: HTTP请求库
- `beautifulsoup4`: HTML解析库
- `Pillow`: 图片处理库
- `ddddocr`: OCR识别库(仅OCR模式需要,体积约20MB)

**注意**: 如果只使用手动输入验证码模式,可以不安装`ddddocr`。

## 使用方法

### 1. 运行程序

```bash
python main.py
```

### 2. 配置信息

在"配置"选项卡中填写以下信息:

- **小程序Authorization**: 从小程序请求头中获取的JWT token
- **网页端Cookie**: 从网页端请求头中获取的完整Cookie字符串
- **公告关键字**: 例如`Day1`, `Day2`等,用于匹配目标公告
- **验证码识别方式**: 选择手动输入或OCR自动识别
- **OCR失败重试次数**: OCR识别失败后的重试次数(超过后自动切换到手动输入)
- **请求线程数**: 多线程请求公告列表的线程数(默认10,可根据网络情况调整)
- **请求超时**: HTTP请求超时时间(秒)

配置完成后点击"保存配置"按钮。

### 3. 执行兑换

切换到"执行"选项卡,点击"开始执行"按钮,程序将自动:

1. 使用多线程高频请求公告列表
2. 查找包含关键字的公告并获取详情
3. 从HTML中提取资格口令
4. 获取验证码(OCR识别或弹窗手动输入)
5. 调用兑换接口完成兑换
6. 显示兑换结果

执行过程中的所有日志会实时显示在界面上,并保存到`logs/`目录下的日期文件中。

## 获取Cookie和Authorization

### 获取小程序Authorization

1. 打开微信小程序"洛克王国:世界"
2. 使用抓包工具(如Fiddler、Charles)抓取请求
3. 找到`https://morefun.game.qq.com/act/v1/api/v1/gateway`请求
4. 复制请求头中的`authorization`字段值

### 获取网页端Cookie

1. 打开浏览器(Chrome/Edge),按F12打开开发者工具
2. 访问`https://rocom.qq.com/act/a20250901certification/`
3. 切换到Network选项卡,刷新页面
4. 找到任意请求,复制请求头中的完整`Cookie`字段值

**安全提示**: Cookie和Authorization包含敏感信息,请勿泄露给他人。

## 打包为EXE

使用PyInstaller将程序打包为独立exe文件:

### 1. 安装PyInstaller

```bash
pip install pyinstaller
```

### 2. 打包命令

```bash
pyinstaller --onefile --windowed --name "洛克王国自动激活" --icon=icon.ico main.py
```

参数说明:
- `--onefile`: 打包为单个exe文件
- `--windowed`: 不显示控制台窗口(GUI程序)
- `--name`: 生成的exe文件名
- `--icon`: 程序图标(可选,需要准备.ico文件)

打包完成后,exe文件在`dist/`目录下。

### 3. 打包注意事项

如果使用OCR模式,需要额外配置:

```bash
pyinstaller --onefile --windowed --name "洛克王国自动激活" \
    --hidden-import=ddddocr \
    --collect-data ddddocr \
    main.py
```

这会增加exe文件体积(约100MB+),但可以独立运行OCR功能。

**建议**: 如果追求小体积,打包时不包含ddddocr,只使用手动输入模式,exe大小约10MB。

## 常见问题

### Q1: 请求公告列表总是超时?

**A**: 检查以下几点:
- Cookie和Authorization是否过期(重新获取)
- 网络连接是否正常
- 尝试增加"请求超时"时间
- 尝试减少"请求线程数"

### Q2: 提取口令失败?

**A**: 公告HTML格式可能变化,请检查:
- 确认公告中确实包含资格码
- 查看日志中的错误信息
- 如有需要,可联系开发者更新提取规则

### Q3: OCR识别总是失败?

**A**: 验证码OCR识别准确率约60-80%,建议:
- 使用"手动输入"模式(更可靠)
- 或设置较高的"OCR失败重试次数",超过后自动切换手动输入

### Q4: 兑换提示"验证码错误"?

**A**:
- 手动输入时请仔细辨认验证码(注意大小写)
- 验证码有时效性,如果识别太慢可能失效,需重新获取

### Q5: 兑换提示"口令已被使用"?

**A**: 资格码有数量限制,先到先得,说明已被抢完,请等待下次活动。

## 技术架构

- **语言**: Python 3.8+
- **GUI框架**: Tkinter(Python标准库,无需额外安装)
- **HTTP请求**: requests
- **HTML解析**: BeautifulSoup4
- **OCR识别**: ddddocr(基于深度学习的中文OCR)
- **多线程**: threading(Python标准库)

## 代码规范

- 所有模块都有完整的文档字符串
- 遵循PEP 8代码规范
- 关键逻辑都有注释说明
- 错误处理完善,不会因异常崩溃

## 免责声明

本工具仅供学习交流使用,请遵守洛克王国相关服务条款。使用本工具产生的任何后果由使用者自行承担。

## 开源协议

MIT License

## 更新日志

### v1.0.0 (2025-10-24)
- ✅ 初始版本发布
- ✅ 支持多线程高频请求
- ✅ 支持OCR和手动输入两种验证码模式
- ✅ GUI图形化界面
- ✅ 配置持久化和日志记录
