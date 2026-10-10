# 青溪镇像素资产规格 · ASSET_SPEC（v1）

> 任务：**T72-pixel-asset-library** ｜ 作者：pixel-asset-artist ｜ 日期：2026-10-10
> 归属：**前端展示层**（`code/frontend/`）。**只读展示**——不参与世界判定，**不触碰 `engine/`、`config/`**（引擎已冻结）。
> 生成方式：**确定性代码生成真·像素**（Python/Pillow 逐像素绘制）。本机**图像生成不可用**，不依赖文生图。
> 对齐：尺寸/网格已与 **art-director**（T71 `LAYOUT`：世界 1440×1080、tile=32）确认；引用契约已与 **frontend-dev** 确认（`id → file`，逐 `place_id` 出图）。

---

## 0. 一句话

本库是**独立、可引用、可复现**的像素资产集合：每个资产有稳定 **id**、单/多张透明底 PNG、可核验 **sha256**；同一脚本运行两次产出**逐字节一致**的 PNG。前端按 id 引用即可，与现行 AI Town 素材（`assets/tileset.png` / `peeps.png`）**解耦并可回退**。

---

## 0.1 ⚠️ 资产接口冻结 v1（2026-10-10，供渲染层 T87 依赖）

**冻结项**（变更需走版本协商；渲染层可**现在**据此切换，不会因画面迭代返工）：

| 冻结内容 | 约定 |
|---|---|
| **id 命名** | `<type>.<name>`，type ∈ {`tile`,`road`,`place`,`char`,`prop`,`icon`}；建筑 = `place.<place_id>`（17 个真实 place_id） |
| **尺寸** | `place.*` **128×128**；`char.*` **144×96**（单帧 48×96 ×3）；`prop.*` **32×48**；`tile.*`/`road.*` **32×32**；`icon.*` **32×32** |
| **锚点** | `place.*` **(64,120)**；`char.*` **(24,92)**（每帧底中）；`prop.*` **(16,44)**；`tile/road` **(0,0)**；`icon` **(16,16)** |
| **透明底** | 全部透明底；**不烘投射阴影**（接地软影由渲染层施加） |
| **清单** | `assets_manifest.json` 的 `id/file/size/anchor` 字段与 `palette/anchorConvention` 结构不变 |

**未冻结（可在同尺寸内自由迭代）**：**画面内容/画风**——如建筑从"俯视正交"升级为**正面 2.5D**、材质/ramp/附属物细化等，**尺寸与锚点不变**。

---

## 1. 尺寸体系与网格

| 类别 | 单帧尺寸 | 网格/锚点 | 说明 |
|---|---|---|---|
| **tile（地形/地面）** | **32×32** | 锚点 (0,0)，**可无缝平铺** | 草地/水/沙/土/农田；正交俯视，非等距 |
| **road（道路/铺装）** | **32×32** | 锚点 (0,0)，**可无缝平铺** | 土路/石街/铺装/木桥 |
| **building（建筑）** | **128×128** 单元 | 锚点 **底边中心 (64, 120)** | 每 `place_id` 一张；脚在 y=120，下方留透明；**不烘焙阴影** |
| **character（角色）** | **48×96** / 帧，**3 帧行走**（sheet **144×96**） | 每格锚点 **底边中心 (24, 92)** | 屏上约 34px（缩放 0.46），与现行 peeps 同口径 |
| **prop（道具/装饰）** | **32×48** | 锚点 **底边中心 (16, 44)** | 树/灌木/石/花/路灯/长椅/招牌/围栏/花坛/木箱/酒桶/水井 |
| **icon（事件图标）** | **32×32** | 锚点 **中心 (16, 16)** | 69 个事件族图标；另出「单色白」版；整表合并 `icons_atlas.png`（供审计台 `ICON_ATLAS`） |

- **基准图块步长 TILE = 32px**，与 `frontend/src/sprites.js` 的 `TILE=32`、art-director `LAYOUT` 一致。
- **世界**：1440×1080（前端展示层）。
- **投影/阴影**：**资产一律不含阴影**（底边以下保持透明）。贴地投影与接触暗线由**渲染层**统一施加（art-director 口径），避免双重阴影。

---

## 2. 统一调色板

### 2.1 基色：**Sweetie 16**（Lospec，白天主锚）

| # | hex | # | hex | # | hex | # | hex |
|---|---|---|---|---|---|---|---|
| 1 | `#1a1c2c` | 5 | `#ffcd75` | 9 | `#29366f` | 13 | `#f4f4f4` |
| 2 | `#5d275d` | 6 | `#a7f070` | 10 | `#3b5dc9` | 14 | `#94b0c2` |
| 3 | `#b13e53` | 7 | `#38b764` | 11 | `#41a6f6` | 15 | `#566c86` |
| 4 | `#ef7d57` | 8 | `#257179` | 12 | `#73eff7` | 16 | `#333c57` |

来源：<https://lospec.com/palette-list/sweetie-16>（调色板归原作者，使用保留署名）。

### 2.2 明度 ramp（派生规则，**不引入新色相**）

Sweetie 16 **没有棕/土/木色相**，而小镇有土路、木屋、农田。按 art-director 认可的做法：

- **同色相明度 ramp**：对任一 Sweetie 16 基色施加 **亮度系数 ×0.5 / ×0.72 / ×0.85 / ×1.15 / ×1.2**（RGB 等比缩放，clamp），得到阴影/高光；
- **棕/土/木**：由**暖色相**（`orange #ef7d57`、`yellow #ffcd75`）派生（例：`orange×0.5 ≈ #773e2b` 木暗、`yellow×0.66 ≈ #a8874d` 土）；
- **总有效色 ≤ 48**（16 基色 + 受控 ramp），全库共用**同一份派生表**，保证跨资产一致。

> 规则固化在 `frontend/tools/gen_assets_pixel.py` 的 `PALETTE` / `shade() / mix()`；改配色只需改该处，全部资产同步更新（可参数化）。

### 2.3 分层用色（承接 T69 风格指南）

- **地形**：压饱和、拉明度，作背景；
- **建筑**：抬明度对比、保留类别色相以区分功能；
- **角色**：高饱和 accent（暖色/亮色）从环境"弹出"；
- 单一光源在**左上前**；平涂为主，克制 dither；无体积光、无等距、无抗锯齿。

---

## 3. 命名与目录

```
frontend/assets/
  ASSET_SPEC.md            ← 本文档
  assets_manifest.json     ← 清单（id → 文件 → 尺寸 → 锚点 → 调色板 → sha256）
  preview_sheet.png        ← 接触表（人眼评估风格统一）
  generated/
    tiles/<name>.png            tile.grass_1 ...
    roads/<name>.png            road.dirt_path / road.stone_street / road.cobble / road.bridge
    buildings/<place_id>.png    place.<place_id>（17 个真实 place_id）
    characters/<name>.png       char.villager_<accent>（144×96 sheet，3 帧）
    props/<name>.png            prop.lamp / prop.tree ...
```

**id 规范**：`<type>.<name>`，type ∈ {`tile`, `road`, `place`, `char`, `prop`}。

- 建筑 id **`place.<place_id>`**（与前端点击映射的 `__placeId` 对齐）；文件 `generated/buildings/<place_id>.png`；
- 角色 id `char.<name>`；道具 `prop.<name>`；地形 `tile.<name>`；道路 `road.<name>`。

**引用（演示加载器，不改变现有 `assets/` 路径，不破坏 smoke_test）**：

```js
const A = await HITTAssets.load("assets/assets_manifest.json");
const tex = A.texture("place.residence");   // → PIXI.Texture（NEAREST）
A.anchor("place.residence");                // → [64, 120]（底边中心）
```

---

## 4. manifest schema（`assets_manifest.json`）

```json
{
  "schema": "hitt.assets/1",
  "generated_by": "frontend/tools/gen_assets_pixel.py",
  "grid": 32,
  "world": { "width": 1440, "height": 1080 },
  "palette": {
    "name": "Sweetie 16 (+same-hue ramp)",
    "base": ["#1a1c2c", "...", "#333c57"],
    "source": "https://lospec.com/palette-list/sweetie-16",
    "ramp": "same-hue brightness ×0.5–1.2, total ≤48 effective colors"
  },
  "anchorConvention": "bottom-center (x=w/2, y=anchorY); no baked shadow",
  "assets": [
    {
      "id": "place.residence", "type": "building",
      "file": "generated/buildings/residence.png",
      "size": [128, 128], "anchor": [64, 120],
      "category": "living", "frames": 1,
      "sha256": "…"
    },
    {
      "id": "char.villager_green", "type": "character",
      "file": "generated/characters/villager_green.png",
      "size": [144, 96], "frameSize": [48, 96], "frames": 3, "anchor": [24, 92],
      "sha256": "…"
    }
  ]
}
```

字段说明：`id / type / file / size / anchor` 必需；`frameSize / frames`（动帧）、`category`（功能色/图例）、`sha256`（复现校验）为扩展字段。

### 4.1 事件图标（T76/T77 扩展）

- **id `icon.<key>`**，`key` 取 `src/sprites.js` 的 `EVENT_ICONS`（**69 个**，单一真源）；
- 每 key 出两版：`generated/icons/<key>.png`（**族色/语义色**，取自 `EVENT_STYLE[ev].color`）与 `generated/icons/<key>_white.png`（**单色白**）；
- 颜色映射固化在 `gen_assets_pixel.py` 的 `ICON_COLOR`（与 EVENT_STYLE 一致），**禁用 emoji**；
- **图集（供审计台直接用）**：`generated/icons_atlas.png` / `icons_atlas_white.png`（32px 格、12 列），manifest 的 `iconAtlas` 给出 `{url, size, cols, index:{key:i}}`，可**直接喂给** `frontend/src/audit.js` 期待的 `HITTSprites.ICON_ATLAS`。


---

## 5. 确定性 / 复现

- **确定性**：整数网格、无随机（如需分布用固定哈希 `h2(x,y,salt)`）、无 AA、锁定调色板；同脚本 → 同像素。
- **逐字节一致**：Pillow 以固定参数（`format="PNG", optimize=False`）写出；两次运行的 PNG **sha256 相同**。
- **校验命令**：
  ```bash
  python3 frontend/tools/gen_assets_pixel.py --set all
  sha256sum frontend/assets/generated/**/*.png   # 与 manifest 内 sha256 对照
  python3 frontend/tools/gen_assets_pixel.py --set all && sha256sum …  # 二次运行哈希不变
  ```

---

## 6. 来源与许可

| 资产 | 来源 | 许可/归属 |
|---|---|---|
| 全部 `generated/**`（tile/road/building/character/prop） | **本项目自制**（`gen_assets_pixel.py` 确定性生成） | 本项目；无第三方素材 |
| 调色板 Sweetie 16 | Lospec，作者 **GrafxKid** | 使用保留署名 https://lospec.com/palette-list/sweetie-16 |
| 参考（不在库内、不参与拼接） | `assets/tileset.png`/`peeps.png`（AI Town）、`v1.2/evidence/style-refs/` | 见 `frontend/NOTICE`、`THIRD_PARTY_NOTICES.md` |

> 若后续用 CC0 现成素材（如 Kenney.nl）补充，须放入 `assets/thirdparty/` 并在 manifest 单独登记 `source` 与 `license` 字段，且**不覆盖**本库自制资产。

---

## 7. 回退与兼容

- 现行 AI Town 素材（`assets/tileset.png` / `peeps.png`）**保留为回退**，`src/town.js` 现有加载路径不变；
- 本库**独立存在**：新增资产不删不改现有素材；`smoke_test.js` 保持全绿（只加载 `data/sprites/town/replay/audit`，本库自带 `src/assets.js` 不进入其依赖）；
- 是否把 `town.js`/`sprites.js` 切换到本库，由 **art-director** 决定；本任务只负责**建库 + 清单 + 演示加载器**。

---

## 8. 手绘像素网格写法（T88，用户倾向手绘）

**手绘优先**：关键可见资产（建筑/角色/道具/事件卡场景/图标）以**文本像素网格 `.px` 为唯一真源**，由 `render_pixel_grid.py` 确定性渲染 PNG。

- **格式**：逐行字符，每字符=1 像素；`#` 注释；`.`/空格=透明；字符→`assets/palette.json` 的键。
- **渲染**：`python3 <skill>/scripts/render_pixel_grid.py <grid.px> <out.png> [--scale N]`（NEAREST、逐字节一致、可哈希）。
- **编辑/扩展**：直接改 `.px` 文本即可（新建筑照抄 `cottage_2p5d.px` 改字符）；新色在 `palette.json` 加键。
- **尺寸**：仍按 §0.1 冻结（`place.*` 128×128 anchor(64,120)…）；手绘网格画完可 NEAREST 缩放到该尺寸。
- **分工**：**手绘**=建筑/角色/道具/图标/事件卡场景；**程序化(②)**=tile/road 等大规模重复（辅助）。
- 详见 `HAND_GRID.md`；样例 `hand/cottage_2p5d.png`、`hand/character_2p5d.png`、`references/hand/*.px`。
