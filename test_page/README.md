# 测试页面功能模块

独立的测试页面功能，用于内部测试。

## 配置

在 `.env` 文件中设置：

```bash
# 启用测试页面
ENABLE_TEST_PAGE=true

# 禁用测试页面（生产环境）
ENABLE_TEST_PAGE=false
```

## 访问地址

启动服务后访问：

- 本地：`http://localhost:8000/static/mobile_final.html`
- 局域网：`http://你的IP:8000/static/mobile_final.html`
- 商家后台原型：`http://localhost:8000/static/merchant_console.html`

## 删除此功能

如果不需要此功能，直接删除整个文件夹：

```bash
rm -rf test_page/
```

项目不会受任何影响！

## 文件结构

```
test_page/
├── __init__.py         # 主模块
├── README.md           # 说明文档
└── static/
    ├── mobile_final.html       # 移动端测试页
    └── merchant_console.html   # 商家后台原型页
```
