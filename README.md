# Book Teardown · 拆书

一个开源的书籍深度解读项目：每本书一个解读系列，每篇文章只回答**一个核心问题**。非虚构拆解观点与知识地图，文学作品细读人物、主题与写法，并明确区分**事实、作者观点与不同解释**。

## 特性

- **问题导向**：每篇解读的文件名即核心问题，一篇只讲透一件事
- **分层拆解**：观点 / 事实 / 争议明确分层，不混淆作者立场与客观描述
- **自包含静态页面**：所有 HTML 内置样式与脚本，明暗主题 + 多套配色，侧边 TOC，Mermaid 图，无需构建
- **SEO 就绪**：canonical / Open Graph / Twitter Card / JSON-LD / sitemap 一应俱全

## 在线阅读

- **Vercel**：<https://book-teardown.vercel.app>
- **本地**：直接打开根目录的 `index.html`，或起一个静态服务：

```bash
open index.html                 # macOS 直接打开总目录
python3 -m http.server 8000     # 或访问 http://localhost:8000
```

## 目录结构

```
book-teardown/
├── index.html                    # 总目录（42 个系列 · 785 篇解读）
├── 人类简史/
│   ├── index.html                # 该系列的卡片目录页
│   ├── 00｜系列拆解与目录.md/.html # 导读：简介 / 知识地图 / 阅读顺序
│   ├── 01｜xxx.md                # 解读原稿（Markdown）
│   └── 01｜xxx.html              # 排版后的阅读页
├── assets/                       # 图标 / OG 封面
├── tools/                        # 后处理与 SEO 脚本
│   ├── postprocess.py            # 裸 HTML -> 站点标准形态 + 目录/README 同步
│   ├── seo.py                    # meta/OG/JSON-LD 注入 + sitemap/robots/404 生成
│   └── books.json                # 书目分类与卡片文案映射
└── …                             # 共 42 个书籍目录
```

## 收录书籍（42 本）

| 分类 | 书目 |
|---|---|
| AI 与智能 | AI文明史·前史 · 智人之上 · 智能简史 · 芯片战争 |
| 人类大历史 | 人类简史 · 未来简史 · 今日简史 · 枪炮病菌与钢铁 · 大灭绝时代 |
| 生命与进化 | 人体简史 · 基因传 · 复杂生命的起源 · 王立铭进化论讲义 · 生命是什么 · 生命进化的跃升 · 癌症传 · 细胞传 · 自私的基因 · 遗传的革命 |
| 经济与社会 | 原则 · 国家为什么会失败 · 大国大城 · 置身事内 · 薛兆丰经济学讲义 · 贫穷的本质 · 随机漫步的傻瓜 · 黑天鹅 · 反脆弱 · 非对称风险 · 巴黎，资本之都的诞生 · 世界的逻辑 · 马克思与《资本论》 |
| 心理与思维 | 亲密关系 · 影响力 · 权力的48条法则 · 思考，快与慢 · 被讨厌的勇气 |
| 文学与政治寓言 | 一九八四 · 动物农庄 · 双城记 · 远大前程 |
| 工程与技术 | 重构-改善既有代码的设计 |

## 写作规范

- `00｜系列拆解与目录`：全书简介、核心问题分层表、知识地图（Mermaid）、全系列目录与推荐星级、阅读顺序。
- 每篇解读只回答**一个核心问题**（文件名即问题），正文区分观点 / 事实 / 争议。
- Markdown 原稿与 HTML 成品同名并存，改稿后重新生成 HTML 即可。

## 开发

工具脚本依赖 Python 3 与 Pillow：

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pillow

# 新增/更新一本书后，补齐站点标准元素并同步目录与 README
python3 tools/postprocess.py 黑天鹅          # 指定书目，不指定则全部
python3 tools/postprocess.py --check        # 只检查缺项，不写盘

# 重新注入 SEO 并生成 sitemap.xml / robots.txt / 404.html / og-cover.png
BASE_URL=https://your-domain.com python3 tools/seo.py
```

## License

本项目以 [MIT License](https://opensource.org/licenses/MIT) 发布，包括 `tools/` 下的脚本与全部解读文章。书中引用与讨论的原著版权归原出版方及作者所有。
