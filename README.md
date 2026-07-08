# Fed No Watch · 联储观察

每天自动收集美联储相关新闻、官员发言、市场利率预期，按时间线展示。

- Twitter / X: https://x.com/tombell_eth
- 项目地址: https://github.com/kindle0088-sys/fed-no-watch

## 数据来源

| 来源 | 类型 | 说明 |
|------|------|------|
| [Federal Reserve RSS](https://www.federalreserve.gov/feeds/feeds.htm) | 官方 | 新闻稿、FOMC声明、官员演讲全文 |
| [华尔街见闻 API](https://wallstreetcn.com) | 媒体 | 美联储相关中英文新闻报道和分析 |
| [FRED](https://fred.stlouisfed.org/) | 经济数据 | 有效联邦基金利率 (EFFR) |
| [CME FedWatch](https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html) | 市场预期 | 联邦基金利率市场概率 |

## 项目结构

```
fed-no-watch/
├── index.html          # 首页：新闻时间线
├── speech.html         # 官员发言专页
├── rate.html           # 利率工具页
├── assets/
│   ├── css/style.css   # 暗色主题样式
│   └── js/
│       ├── data.js     # 编译后的数据 (由build_data.py生成)
│       └── app.js      # 共享渲染逻辑
├── tools/
│   ├── collect_fed.py         # 采集Fed官方RSS
│   ├── collect_wallstreet.py  # 采集华尔街见闻
│   ├── build_data.py          # 合并去重排序 + 生成data.js
│   └── requirements.txt       # (可选) Python依赖
├── .github/workflows/
│   └── collect.yml    # GitHub Actions 定时采集
└── .gitignore
```

## 本地使用

### 手动采集

```bash
python3 tools/build_data.py
# 输出 → assets/js/data.js
```

### 本地预览

```bash
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

## GitHub Actions 自动采集

项目配置了每小时自动采集的 GitHub Actions workflow：

1. 每天早上8点到晚上12点，每2小时运行一次（可调整）
2. 采集 → 合并 → 构建 → 提交 → 推送到 GitHub Pages

## 免责声明

本网站仅供个人学习和参考，不构成投资建议。
利率概率数据来源于CME FedWatch公开页面，可能存在延迟。
