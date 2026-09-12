# 便利店调酒

60 款便利店调酒配方速查，支持分类搜索、收藏、虚拟购物车和采购清单。

网站：https://www.200jin.cn/cocotail/

纯 HTML、CSS、JavaScript，无构建依赖。GitHub Pages 从 main 分支根目录发布。

收藏、购物车和采购勾选保存在当前浏览器的 localStorage 中，不会上传到服务器。

## 分享卡片

每款配方都有一张 1080px 宽的竖版卡片（`assets/cards/card-NN.png`，NN 即该配方在 `index.html` 的 `R` 数组中的序号，从 1 起），
在详情弹层底部点「下载调酒卡片」即可保存，文件名形如 `自由古巴·便利店调酒.png`。
卡片是静态文件，只在点击时才请求，不影响页面加载。

卡片沿用站点深色视觉：主视觉从 `assets/cocktails-sprite.webp` 裁格并做径向羽化，
分类色决定光晕、胶囊标签和配比文字的颜色。

## 重新生成卡片

改了配方或想调样式后重新出图（需要 Pillow 与 Node）：

```bash
node scripts/extract-drinks.mjs          # 从 index.html 抽配方 → scripts/drinks.json
python3 scripts/build-cards.py           # 渲染全部 60 张
python3 scripts/build-cards.py 自由古巴 可乐桶   # 只渲染指定几杯，方便调样式
```

- `scripts/extract-drinks.mjs` 直接解析 `index.html` 里的 `CATS` / `R` / `SPRITE_NAMES`，改配方后不用维护第二份数据。
- `scripts/drinks.json` 是构建产物，已忽略提交。

## 直达某一杯

`https://www.200jin.cn/cocotail/#自由古巴` 会直接打开该配方的详情弹层，方便分享单杯。
