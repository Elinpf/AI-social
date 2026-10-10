# style-refs 清单（T69 目标参考图 · 归属与来源）

> 用途：作为「青溪镇」像素风的**风格锚 / 目标观感**，供 art-director 调色板与 frontend-dev 对比。
> ⚠️ 这些图**不是可直接拼接的 tileset**（像素网格、尺寸、一致性都无法直接嵌入我们的确定性渲染）。

生成方式说明：本机**图像生成不可用**（`baoyu-image-gen` 的 `codex-cli` 目标 `codex exec` 挂起超时、锁无法获取），故按任务允许的 fallback —— **公开源筛选 + 自绘色卡**，并逐条登记归属。

| 文件 | 类别 | 来源 / 生成方式 | 实际 prompt 或出处 | 归属/许可 |
|---|---|---|---|---|
| `ref_aitown_day.png` | 白天小镇（目标观感） | 下载自 a16z AI Town 官方仓库 README 内嵌截图 | 官方截图（AI Town 招牌画面：草地+土路+角色交谈+聊天面板） | a16z-infra/ai-town，MIT；源 URL https://github.com/a16z-infra/ai-town |
| `ref_aitown_night_derived.png` | 夜间小镇（**派生示意**） | 由 `ref_aitown_day.png` 用 PIL 做亮度 0.42× + 冷蓝 tint 派生 | 非官方夜间截图，**仅示意夜间氛围/低明度冷调** | 派生自 AI Town 截图（MIT） |
| `ref_character_peeps.png` | 角色特写 | 从 `code/frontend/assets/peeps.png` 裁切（cols 1–11, rows 4–5）放大 4× | AI Town 角色立绘（本项目已在用） | a16z-infra/ai-town，MIT；出处见 `frontend/NOTICE` |
| `ref_palette_day_sweetie16.png` | 白天配色 | 用 PIL 绘制色卡，取 Lospec「Sweetie 16」 | 明亮白昼·乡土小镇 16 色锚 | 调色板：Sweetie 16, Lospec https://lospec.com/palette-list/sweetie-16 |
| `ref_palette_night_vinik24.png` | 夜间配色 | 用 PIL 绘制色卡，取 Lospec「Vinik24」 | 夜间/黄昏·低明度冷暖锚 | 调色板：Vinik24 by Vinik, Lospec https://lospec.com/palette-list/vinik24 |
| `ref_palette_general_resurrect64.png` | 通用配色 | 用 PIL 绘制色卡，取 Lospec「Resurrect 64」 | 通用大地图 64 色·明度分层充分 | 调色板：Resurrect 64 by Kerrie Lake, Lospec https://lospec.com/palette-list/resurrect-64 |

> 生成脚本：`/tmp/gen_refs.py`（PIL + Lospec JSON API）。色卡为**自绘衍生作品**，调色板本身按其作者署名（上述 URL）。
