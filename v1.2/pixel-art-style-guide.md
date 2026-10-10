# 青溪镇像素风 · 风格指南（v1.2）

> 任务：T69-pixel-style-guide-and-refs　｜　作者：visual-researcher　｜　日期：2026-10-10
> 面向：art-director（调色板/构图/密度）、frontend-dev（渲染口径）、leader（转用户）
> 硬约束遵守：**只读**——未改前端代码、未碰 `engine/`。

---

## 0. 结论：用户的提示词库「有用，但必须筛选」

用户给出的一大批像素风关键词，**大部分能直接用作"风格锚"**（尤其"16-bit / clean pixel art / Stardew-like / 有限调色板"），但其中**约 1/3 与我们的目标冲突**（等距、3D/体积光、赛博/蒸汽波、写实渐变、矢量描边风），**若整串丢给生成器会把我们带偏**。

**主风格定位（建议拍板）**：

> **16-bit 时代的 clean pixel art；明亮、乡土、Stardew-like 的俯视 2D 小镇；有限调色板（16–64 色）；以平涂为主 + 克制的抖动；无体积光、无等距、无 3D。**

这与 leader 指定方向（俯视 2D 小镇 / Stardew-like 明亮乡土 / 有限 16-bit 调色板）一致。

---

## 1. 关键词筛选表

图例：✅ 适配（主选）｜🟡 慎用（限定用法/只取部分）｜❌ 排除（会带偏，勿用）

### ① 位深度
| 关键词 | 判定 | 说明 |
|---|---|---|
| **16-bit** | ✅ 主选 | SNES/Genesis 时代。色彩丰富但仍有限，最贴合明亮小镇。**我们的基准位深**。 |
| 24-bit | 🟡 慎用 | 真彩平滑渐变会**失去像素感**；仅允许极少量用于天空/光照过渡，不可作主调。 |
| 8-bit | 🟡 慎用 | NES 级色数太少，主场景会显得干瘪；可用于 **HUD/图标**等小元素。 |
| 2-bit / 1-bit | ❌ 排除 | 黑白/四色无法承载小镇的信息量与可辨识度。 |

### ② 游戏机
| 关键词 | 判定 | 说明 |
|---|---|---|
| **Sega Genesis / SNES** | ✅ 主选 | 16-bit 平台调性，正是我们要的年代感。 |
| PS1 | 🟡 慎用 | PS1 特征其实是"低模 3D + 抖动 + 写实纹理"，与平涂像素不同。**只取其 dither 抖动技巧，不取 3D**。 |
| Atari | ❌ 排除 | 色数/分辨率过低。 |
| Dreamcast | ❌ 排除 | 已是 3D 世代，与本风格无关。 |

### ③ 年代
| 关键词 | 判定 | 说明 |
|---|---|---|
| **80s–90s（偏 90s）** | ✅ 主选 | 90s = 16-bit 黄金期，正好。80s 更接近 8-bit，色少。 |
| vaporwave | ❌ 排除 | 霓虹紫粉渐变、网格、日式复古，与"乡土明亮小镇"直接冲突。 |

### ④ 游戏名风格
| 关键词 | 判定 | 说明 |
|---|---|---|
| **Stardew Valley** | ✅ 主参考 | 明亮、乡土、正交俯视、可读性强——**leader 指定方向**，作首锚。 |
| **Owlboy** | ✅ 可参考 | 高密度优质像素、明快配色、细节丰富；取其**配色与细节密度**。 |
| Terraria | 🟡 慎用 | 侧视 2D、偏土黄、密度极高；只取"瓦片过渡/挖掘层次"技巧，**不取视角**。 |
| Cave Story | 🟡 慎用 | 低分辨率、偏暗单色系；只取"清晰轮廓/克制色数"。 |
| Minecraft | 🟡 慎用 | 体素 3D + 16×16 材质；只取"瓦片可无缝平铺"的思路，**不取体素**。 |
| Castlevania / Metal Slug | ❌ 排除 | 暗黑哥特 / 战争动作，噪声与题材都不符。 |

### ⑤ 其他
| 关键词 | 判定 | 说明 |
|---|---|---|
| isometric（等距） | ❌ 排除 | 我们是**正交俯视/微斜俯视**（orthogonal tile grid），不是菱形等距网格；混用会破坏我们与 AI Town tileset 的**网格一致性**。 |
| volume-lighting（体积光） | ❌ 排除 | 属 3D/写实光效；像素风用**平涂 + 少量 dither**。 |
| dithered gradients（抖动渐变） | 🟡 慎用 | **仅少量**用于天空/水面/夜晚光照过渡；满屏抖动＝噪声（见 T65 报告 P0-1）。 |
| "by albertov" | ❌ 排除 | albertov 是**矢量描边扁平插画**风，不是像素画；会误导生成器产出非像素结果。 |

---

## 2. 配色规范（含具体 palette 与来源 URL）

**分层用色原则**（Slynyrd 的 hue-shift ramp 法）：
- 每条 ramp **明度递增时降饱和、暗部加饱和**，整条 ramp 做**色相偏移**，避免"死板直 ramp"；
- **地形**（草/路/水）**压低饱和、拉开明度**，做背景；
- **建筑**提高明度对比、保留类别色相以区分功能；
- **角色**用**高饱和 accent**（暖色/亮色）从环境中"弹出"；
- 保留 T65 报告结论：**统一描边 + 落脚阴影 + 单一光源（左上前）**。

| 用途 | 建议 palette | 来源 URL |
|---|---|---|
| **白天/乡土主锚（亮暖）** | **Sweetie 16**（16 色，明亮友好） | https://lospec.com/palette-list/sweetie-16 |
| **通用大地图（明度分层充分）** | **Resurrect 64**（64 色，可摘子集） | https://lospec.com/palette-list/resurrect-64 |
| **夜间/黄昏（低明度冷暖）** | **Vinik24**（24 色） | https://lospec.com/palette-list/vinik24 |
| 备选亮调 | Endesga 32 / Apollo | https://lospec.com/palette-list/endesga-32 ｜ https://lospec.com/palette-list/apollo |

> palette 数据经 Lospec JSON API 取得；色卡见 `v1.2/evidence/style-refs/ref_palette_*.png`。调色板归原作者，使用请保留上述署名。

---

## 3. 生成提示词模板（供后续生成/参考）

**正向模板**：
```
16-bit pixel art, top-down 2D day/night cozy rural town, Stardew-Valley-like,
clean pixel clusters, limited 32-color palette, dirt path + cobble stone street,
small houses with tiled roofs, sparse trees and bushes, minimal dithering,
crisp pixels, single top-left light source, readable silhouettes, no text
```
**负向（勿出现）**：
```
isometric, 3D render, volumetric lighting, cyberpunk, neon, vaporwave,
photorealistic, smooth gradients, oversaturated, anti-aliasing, vector outline style
```

---

## 4. 目标参考图（3–6 张，落 `v1.2/evidence/style-refs/`）

| 文件 | 类别 | 来源/生成 | prompt / 出处 |
|---|---|---|---|
| `ref_aitown_day.png` | 白天小镇 | a16z AI Town 官方 README 截图（下载） | 官方画面（草地+土路+角色交谈+聊天面板）https://github.com/a16z-infra/ai-town |
| `ref_aitown_night_derived.png` | 夜间小镇（派生示意） | 上述白天帧 PIL 调暗 0.42× + 冷蓝 tint | 非官方夜截图，仅示意夜间低明度冷调 |
| `ref_character_peeps.png` | 角色特写 | 本项目 `assets/peeps.png` 裁切放大 4× | AI Town 角色立绘（MIT，见 `frontend/NOTICE`） |
| `ref_palette_day_sweetie16.png` | 白天配色卡 | PIL 自绘（取 Lospec 数据） | palette: sweetie-16 |
| `ref_palette_night_vinik24.png` | 夜间配色卡 | PIL 自绘 | palette: vinik24 |
| `ref_palette_general_resurrect64.png` | 通用配色卡 | PIL 自绘 | palette: resurrect-64 |

> 归属与来源明细见 `v1.2/evidence/style-refs/manifest.md`。
> **生成方式说明**：本机图像生成不可用（`baoyu-image-gen` 的 `codex-cli` 目标 `codex exec` 挂起超时、锁无法获取，实测 4 次失败），故按任务允许回退为**公开源筛选 + 自绘色卡**并登记归属。

---

## 5. ⚠️ 重要声明（必须转达用户 / frontend-dev）

**以上所有参考图（含生成的与搜集的）仅为「参考 / 风格锚」，不是可直接拼接使用的 tileset。**
像素网格、单像素对齐、tile 边距、调色板一致性都无法直接嵌入我们的渲染管线；直接贴用会出现**网格错位、接缝、色偏**。

**最终素材仍以「AI Town tileset（`gentle-obj.png` / `peeps.png`，MIT）+ 我们现有的确定性渲染」为准**；本指南的作用是**定调色板、定构图/密度、做验收锚**，不是替换素材。

---

## 6. 交接

- **art-director**：以 §2 的 palette + 分层原则校准青溪镇调色板；用 §1 的 ✅/🟡/❌ 清单约束后续参考图与生成提示词。
- **frontend-dev**：确认渲染沿用 AI Town tileset + 确定性布局；如需新增瓦片，走 CC0/授权来源并登记（见 T65 报告 R7）。
- **leader**：§0 的主风格定位与 §5 的声明可直接转用户。
