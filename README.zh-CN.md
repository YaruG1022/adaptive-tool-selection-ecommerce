# 电子商务智能体的自适应工具选择（Adaptive Tool Selection for E-Commerce Agents）

[English](README.md) | [简体中文](README.zh-CN.md)

本项目研究自主电子商务智能体（autonomous e-commerce agent）在存在不确定性和成本时，应何时获取信息、选择哪一种工具，以及何时停止调查。

**当前成果：** Little Signal Shop（小信号商店）是可独立运行的浏览器原型（browser prototype），包含仓库动画、研究工作台和只读经营回放（read-only business replay）。仓库（repository）还包含初版分阶段实施计划（phased implementation plan），并为后续研究代码建立了目录骨架（directory scaffold）。

**当前状态：** 深度 Q 网络（Deep Q-Network, DQN）训练和 Python 研究环境尚未实现。浏览器中的比较使用简化模拟（simulation）下的三种固定策略（fixed policies），不构成经过验证的研究结论，也不能作为学习型智能体（learned agent）性能的证据。

## 研究方向（Research direction）

研究暂定题目为 *RL-Guided Adaptive Tool Selection for Long-Horizon Autonomous E-Commerce Agents*，属于 CPTS 580 的 Topic B: New Application。题目中的强化学习（reinforcement learning, RL）描述计划中的研究方法。

计划中的控制器（controller）在需求预测（demand forecasting）、市场调查（market research）、供应商分析（supplier analysis）、库存分析（inventory analysis）、定价分析（pricing analysis）和停止调查之间选择。独立且固定的经营策略（business policy）负责采购与定价，使比较能够聚焦工具选择的影响。评估计划（evaluation plan）要求匹配市场条件、采用多个训练随机种子（training random seeds）、使用留出市场（held-out markets），并明确计入信息成本。

[项目总计划](FINAL_PROJECT_PLAN.md)记录约定的研究范围和限制；[初版实施计划](docs/implementation-plan.md)提出阶段安排及完成标准。两份计划目前以英文维护。

## 运行原型（Run the prototype）

使用当前版本的 Edge、Chrome 或 Firefox 浏览器（browser）打开根目录中的 `index.html`。无需安装软件包（package）、执行构建（build）、注册账户或提供应用程序接口密钥（Application Programming Interface key, API key）。请将 `index.html`、`styles.css`、`i18n.js` 和 `app.js` 保持在同一目录。

界面默认使用英文。顶部的 `中文` / `English` 按钮可切换语言，并保留当前页面、商店状态、实验设置、所选记录及播放状态。刷新后会重新开始一个英文会话（session）。

Lucide 1.17.0 图标（icons）通过固定版本的 unpkg 地址加载。如果该资源不可用，图标可能缺失，经营逻辑和操作控件仍可运行。

## 已实现功能（Implemented features）

| 页面 | 当前功能 |
| --- | --- |
| 仓库（Warehouse） | 付费信息工具、每天最多两次调用、采购、库存、延迟到货、销售、结算，以及拣货、打包和发货动画 |
| 研究实验室（Research Lab） | 在匹配的市场随机种子（market random seeds）下比较不调查、用满工具预算和固定规则；可设置预测可靠度、波动、工具费用和种子数量 |
| 经营回放（Business Replay） | 查看记录中的决策、信息、现金变动、缺货和事后需求；播放原始收据（receipt），不改变当前商店 |

播放支持暂停、变速、跳过和减少动态效果（reduced motion）。实验暂停独立于仓库播放。手动商店从第 28 天开始，研究演示回合（episodes）覆盖第 1 至第 90 天。

所有状态和历史记录都保存在浏览器内存（browser memory）中，刷新即重置。目前没有后端（backend）、数据库（database）、已连接的大语言模型（large language model, LLM）或已保存的训练模型（trained model）。经营轨迹（business trajectories）与学习曲线（learning curves）含义不同。退货、促销及完整的会计与估值模型（accounting and valuation model）仍待实现；当前期末库存折价属于演示假设。

## 实施阶段（Implementation phases）

1. 明确环境、观察、动作、会计、奖励、随机性和记录的规则约定（contracts）。
2. 提取 JavaScript 参考模拟（reference simulation），保持浏览器原型可用。
3. 建立 Python 环境，验证跨语言一致性（cross-language parity），并复现基线比较（baseline comparisons）。
4. 实现并训练深度 Q 网络（Deep Q-Network, DQN）工具选择控制器（controller）。
5. 在留出市场（held-out markets）上评估，报告不确定性、失败情况与限制。
6. 将研究回合记录（episode records）导入现有研究实验室和经营回放页面。

目前仅完成原型保留和目录骨架（directory scaffold）；其余阶段仍为提案。具体完成标准见[实施计划](docs/implementation-plan.md)。

## 仓库结构（Repository structure）

```text
index.html / styles.css / i18n.js / app.js   当前浏览器原型
FINAL_PROJECT_PLAN.md                       约定的研究方向
docs/implementation-plan.md                  初版实施阶段
contracts/                                  预留共享规则约定与数据模式
src/                                        预留浏览器模块拆分
research/configs/                           预留研究设置
research/src/little_signal_shop/             预留 Python 环境与控制器
tests/                                      预留浏览器、规则、研究与参考样例检查
scripts/                                    预留项目命令
artifacts/                                  忽略生成产物，保留目录说明
CODEX_SETUP_INSTRUCTIONS.md                  原始本地与 GitHub 设置说明
```

预留目录包含说明文件或 `.gitkeep` 占位文件（placeholder files），并不代表相应实现已完成。目前没有需要执行的依赖安装（dependency installation）或训练命令。GitHub 仓库改名后，本地目录可继续使用 `little-signal-shop`。

## 验证与限制（Verification and limitations）

初次设置时已检查默认英文、双语切换保留状态、三个页面、单日结算、默认比较的全部 9 个回合、暂停播放及回放隔离（replay isolation）。这些检查用于确认原型行为，不能验证其经济假设。[实施计划](docs/implementation-plan.md#phase-0--preserve-the-prototype)记录了后续回归检查（regression checks）可参考的数值，[测试说明](tests/README.md)列出未来验证职责。

仓库为私有状态（private）。GitHub Pages 未启用；原始导出（export）中的 `.nojekyll` 文件予以保留，其本身不会启用托管（hosting）。

## 许可证（License）

项目尚未选择许可证（license）。所有者应在按开源许可证（open-source license）分发项目之前明确授权条款。
