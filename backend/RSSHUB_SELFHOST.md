# 自建 RSSHub 最小化部署说明（为「深圳本地」新闻提供真实源）

> 目的：让 life-workbench 的「深圳本地」新闻从「算法从泛源里筛」升级为「真实本地源拉取」。
> 前置：你已经有一个能跑 Docker 的机器（本地或服务器）。
>
> 定位：本项目已在 `config.yaml` 内置 **Google News「深圳」检索源**（免密钥、立即可用，
> 覆盖绝大多数深圳本地报道）。本文件描述的自建 RSSHub + 微信路由，是作为**补充源**——
> 专门补 Google 没收录的本地独家/深度内容（如读特独家、深网观察专栏、深圳新闻网街社
> 共治快报等）。二者并存即可形成完整的深圳本地新闻面，无需二选一。

---

## 1. 现状回顾（为什么需要自建）

- 深圳新闻网 / 读特 / 深圳特区报 **均不提供标准 RSS**（`/rss.xml` 全部 404）。
- 公共 RSSHub 镜像（rsshub.app 已封 feed reader；rsshub.rssforever.com 无深圳本地路由）。
- 因此当前「深圳本地」靠 `news_service._is_local` 从泛源实时筛，内容稀疏。

自建一个 RSSHub 实例，把深圳本地源做成路由，再改 `config.yaml` 的 `rsshub_base` 指向它即可。

---

## 2. 第一步：启动 RSSHub 实例

### 方式 A：Docker（推荐，最简单）

```bash
# 新建目录
mkdir -p rsshub && cd rsshub

# 写最小 docker-compose.yml
cat > docker-compose.yml <<'EOF'
version: "3"
services:
  rsshub:
    image: diygod/rsshub:latest
    restart: always
    ports:
      - "1200:1200"
    environment:
      # 可选：给自己的实例加访问密钥（建议开启，防滥用）
      - ACCESS_KEY=你的密钥
    # 内存/CPU 限制，树莓派或低配机建议加上
    deploy:
      resources:
        limits:
          memory: 512M
EOF

docker compose up -d
```

启动后访问 `http://<你的机器IP>:1200` ，看到 "Welcome to RSSHub" 即成功。
验证路由：`http://<IP>:1200/zhihu/daily` 应返回 XML。

### 方式 B：Node（无 Docker 时）

```bash
git clone https://github.com/DIYgod/RSSHub.git
cd RSSHub
npm install
npm start          # 默认监听 1200
```

---

## 3. 第二步：加深圳本地路由

RSSHub 自带路由有限（多为全国媒体）。深圳本地最稳妥的来源是**微信公众号**，用官方 `weixin` 路由（需配置公众号抓取后端）或社区维护的 `weixin` 中间件。

### 3.1 启用微信公众号路由（推荐，深圳媒体均有公众号）

`weixin` 路由依赖第三方抓取服务（如微信公众号文章抓取 API）。在 RSSHub 环境变量中配置：

```yaml
# docker-compose.yml 的 environment 追加
- WEIXIN_COOKIE=              # 见 3.3
- CACHE_TYPE=memory
- CACHE_EXPIRE=300
```

路由格式：`/weixin/:id`，`:id` 为公众号的 `biz` 或微信号。

| 媒体 | 公众号（示例） | 路由 |
|------|----------------|------|
| 深圳新闻网 | sznews_com | `/weixin/sznews_com` |
| 读特 | dutenews | `/weixin/dutenews` |
| 深圳特区报 | szsnews | `/weixin/szsnews` |

> ⚠️ 公众号 `biz`/微信号需自行从公众号文章链接或抓包获取，上表为示例 id，请实际替换。

### 3.2 写一条自定义路由（无需第三方服务时）

如果某深圳媒体有可被 RSSHub 解析的列表页，可在 RSSHub 的 `routes/` 下新建文件
（示例：`routes/shenzhen/news.js`，需会写 JS + cheerio）：

```js
// routes/shenzhen/news.js
const got = require('@/utils/got');
const cheerio = require('cheerio');

module.exports = async (ctx) => {
  const url = 'https://www.sznews.com/';
  const res = await got(url);
  const $ = cheerio.load(res.data);
  const items = $('.news-list li').slice(0, 20).map((_, e) => {
    const $e = $(e);
    const link = $e.find('a').attr('href');
    const title = $e.find('a').text();
    return { title, link };
  }).get();

  ctx.state.data = {
    title: '深圳新闻网',
    link: url,
    item: items,
  };
};
```

然后在 `routes/shenzhen/router.js` 注册：
```js
module.exports = (router) => {
  router.get('/news', require('./news'));
};
```
路由即：`/shenzhen/news`。

### 3.3 配 ACCESS_KEY 与微信 cookie（可选但建议）

- 实例对外暴露时务必设 `ACCESS_KEY`，否则易被刷爆。
- `weixin` 路由需要有效的微信 `Cookie`（含 `appmsg_token` 等），获取方式见 RSSHub 官方文档「微信公众号」一节。

---

## 4. 第三步：改 config.yaml 接入

把 `rsshub_base` 指向自建实例，并启用本地源：

```yaml
datasource:
  news:
    provider: rss
    update_interval: 600
    rss:
      cache_ttl: 300
      rsshub_base: http://<你的机器IP>:1200   # ← 改成自建实例
      sources:
        # ... 其他源不变 ...
        # ---------- 深圳本地（自建 RSSHub 启用后取消注释）----------
        - url: rsshub://weixin/sznews_com
          category: local
        - url: rsshub://weixin/dutenews
          category: local
        - url: rsshub://weixin/szsnews
          category: local
        - url: rsshub://shenzhen/news          # 若用了 3.2 自定义路由
          category: local
```

> 注意：因为代码里 `rsshub://xxx` 会被拼成 `{rsshub_base}/xxx`，
> 所以只要 `rsshub_base` 指向自建实例，上面这些源就会自动走本地实例。
> 若实例设了 `ACCESS_KEY`，源 URL 需带 `?key=你的密钥`
> （如 `rsshub://weixin/sznews_com?key=你的密钥`）。

### 4.1 与内置 Google News 源共存（推荐）

`config.yaml` 已内置 Google News「深圳」检索源（免密钥、立即可用）。本文件
的微信路由**不需要替换它，而是叠加在它之上**：

- **Google News 源**：覆盖绝大多数深圳本地报道（快、全、免维护）。
- **微信路由源（自建）**：补 Google 没收录的本地独家/深度内容
  （读特独家、深网观察专栏、深圳新闻网街社共治快报等）。

两者 `category` 都为 `local`，进入「深圳本地」后会经 `_local_source_focus`
做关键词聚焦（剔除仅「相关」不含深圳的噪声），再合并去重展示。因此：
**先保留 Google News 源不动，再按需启用微信路由作为补充**，无需二选一。

---

## 5. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 路由返回 404 | 该路由在官方 RSSHub 不存在 | 用 3.2 自定义路由，或确认是否为社区路由 |
| weixin 路由空 | 未配微信 Cookie / Cookie 失效 | 重新抓包更新 `WEIXIN_COOKIE` |
| 实例被打满 | 未设 ACCESS_KEY | 设 `ACCESS_KEY` 并限制并发 |
| 后端读不到本地新闻 | rsshub_base 仍是公共镜像 | 确认已改为自建 IP |
| 单源抓取失败日志 | 该源 URL 不通 | 看 `news_service` 的 `RSS 源抓取失败` 日志排查 |

---

## 6. 最小可行路径（TL;DR）

1. `docker compose up -d` 起 RSSHub（1200 端口）。
2. 配 `WEIXIN_COOKIE`，用 `/weixin/:id` 拉深圳媒体公众号。
3. `config.yaml` 改 `rsshub_base` + 取消注释本地源。
4. 重启后端，「深圳本地」即可真实丰满。
5. **保留 Google News 源**：本文件的微信路由是「补充」而非「替代」，两者并存
   才能覆盖「快讯 + 独家」完整本地新闻面。
