# 开发进度记录

## 文档目标

本文档用于记录项目从设计进入开发后的实际落地进度。

记录原则：

- 只记录已经完成或正在推进的开发工作
- 设计稿已完成不等于开发已完成，两者需明确区分
- 每完成一个可独立验收的部分，就在本文档补充一次
- 每次补充尽量包含时间、范围、结果、遗留问题和下一步

---

## 开发记录

### 2026-04-29

#### 记录 072：完成模块 10 任务 02，实现子任务级 rerank 通道

- 状态：已完成
- 范围：完成模块 10 中“任务 02：实现子任务级 rerank 通道”，先打通单个 `sub-query` 内部候选集的独立 rerank 链路
- 结果：
  - 已新增：
    - `src/mindwiki/llm/rerank_models.py`
    - `src/mindwiki/llm/rerank_service.py`
    - `src/mindwiki/application/subquery_rerank_service.py`
  - 已扩展：
    - `src/mindwiki/infrastructure/settings.py`
    - `src/mindwiki/llm/providers/openai_compatible.py`
    - `src/mindwiki/application/retrieval_models.py`
  - 当前已建立独立 rerank 协议层：
    - `RerankDocument`
    - `RerankRequest`
    - `RerankResult`
    - `RerankResponse`
  - 当前已建立独立 rerank service：
    - `RerankService`
    - `build_rerank_service()`
  - 当前已为 `SiliconFlow` 补齐最小 `/rerank` provider：
    - `OpenAICompatibleRerankProvider`
  - 当前已建立模块 10 第一版应用层 rerank 输出结构：
    - `RerankedSubQueryCandidate`
    - `SubQueryRerankResult`
  - 当前 `SubQueryRerankService` 已可执行：
    - 输入一个 `SubQueryResult`
    - 组装 `(sub_query, chunk)` rerank documents
    - 调用独立 rerank 通道
    - 返回当前 `sub-query` 的 reranked `top 5`
  - 当前 reranker 配置已正式预留：
    - `LLM_RERANK_BASE_URL`
    - `LLM_RERANK_API_KEY`
    - `LLM_RERANK_MODEL_ID`
    - `LLM_RERANK_TIMEOUT_MS`
- 验证结果：
  - `python3 -m py_compile src/mindwiki/llm/rerank_models.py src/mindwiki/llm/rerank_service.py src/mindwiki/application/subquery_rerank_service.py` 通过
  - `python3 -m pytest tests/test_llm_models.py tests/test_llm_provider.py tests/test_retrieval_service.py` 通过
  - 当前共 `33` 个相关测试，全部通过
  - 已新增测试覆盖：
    - rerank 配置读取
    - `SiliconFlow /rerank` payload 与结果解析
    - 单个 `sub-query` rerank 后只保留 `top 5`
- 当前实现边界：
  - 当前只完成单个 `sub-query` 内部 rerank 通道
  - 当前尚未进入：
    - context builder
    - citation payload
    - 真实本地 rerank 验收脚本
  - 当前 `rerank_reason` 先采用最小规则化承接，不额外引入生成式解释链路
- 遗留问题：
  - `SiliconFlow` 真实 `/rerank` 响应字段是否需要兼容更多变体，需在后续真实联调中确认
  - 当前尚未把 rerank 结果继续送入 context builder
- 下一步：
  - 进入模块 10 任务 03：实现 context builder

#### 记录 069：完成模块 10 任务 01，检索编排后半段设计对接与当前代码差异修正

- 状态：已完成
- 范围：完成模块 10 中“任务 01：检索编排后半段设计对接与当前代码差异修正”，对照 `Step 09.4 / 09.5 / 09.6` 与当前已落地的前半段检索编排代码，收敛后半段模块的真实输入、输出与实现边界
- 对照结论：
  - 已核对设计文档：
    - `doc/design/step-09-retrieval-orchestration/09.04-subquery-level-llm-rerank.md`
    - `doc/design/step-09-retrieval-orchestration/09.05-context-builder-truncation-and-assembly.md`
    - `doc/design/step-09-retrieval-orchestration/09.06-citation-payload-structure.md`
  - 已核对当前实现：
    - `src/mindwiki/application/retrieval_models.py`
    - `src/mindwiki/application/query_expansion_service.py`
    - `src/mindwiki/application/subquery_retrieval_service.py`
    - `src/mindwiki/llm/service.py`
    - `src/mindwiki/infrastructure/settings.py`
  - 已确认当前代码已具备可直接作为模块 10 输入的基础对象：
    - `QueryDecomposition`
    - `QueryExpansion`
    - `SubQueryCandidate`
    - `SubQueryResult`
    - `ChunkProjection`
    - `ChunkLocation`
- 当前差异修正结果：
  - 已确认 `9.4 rerank` 当前完全未实现：
    - 没有独立 `rerank` 请求/响应协议
    - 没有 `RerankService`
    - 没有 `RerankedSubQueryCandidate`
    - 没有 `SubQueryRerankResult`
  - 已确认当前 `generate_text` 通道不应直接复用为 reranker 主通道：
    - 当前 `LLMService` 只承接 `/chat/completions` 风格文本生成
    - 当前 reranker 已正式确定采用：
      - `SiliconFlow`
      - `Qwen/Qwen3-Reranker-8B`
    - 因此模块 10 需要新增独立 rerank provider / service
  - 已确认 `9.5 context builder` 当前完全未实现：
    - 没有预算模型
    - 没有上下文分段结构
    - 没有“每个 `sub-query` 先取前 `2` 条代表证据”的拼装逻辑
    - 没有相邻 chunk 局部合并逻辑
  - 已确认 `9.6 citation payload` 当前完全未实现：
    - 没有 `citation_id`
    - 没有 `sub_query_id`
    - 没有 `evidence_role`
    - 没有 `snippet`
    - 没有面向前端/回答层的统一 citation 视图模型
  - 已确认当前 `ChunkLocation` 仅提供：
    - `chunk_index`
    - `section_id`
    - `page_number`
    - `imported_at`
    - 这足够作为 citation 定位层第一阶段输入，但还未转换成正式 citation payload
- 模块 10 后续实现边界已正式收敛为：
  - 任务 02：实现子任务级 rerank 通道
  - 任务 03：实现 context builder
  - 任务 04：实现 citation payload
  - 任务 05：补本地验收脚本、README 与运行说明
- 当前实现决策：
  - `9.4` 只做单个 `sub-query` 内 rerank，不做跨 `sub-query` 全局排序
  - `9.4` 采用独立 reranker 通道，不复用 `generate_text`
  - `9.5` 当前阶段不引入预算控制层
  - `9.6` 直接面向后续回答层输入结构设计，而不是只做调试字段
- 明确不纳入当前模块任务 01 的内容：
  - `Step 10` 回答生成
  - 前端展示格式细化
  - 评估闭环
- 遗留问题：
  - `SiliconFlow` 的 rerank 请求协议与返回结构需在任务 03 中按真实接口对齐
  - `citation payload` 与后续回答层 schema 的最终兼容范围需在任务 04 中收口
- 下一步：
  - 进入模块 10 任务 02：实现子任务级 rerank 通道

#### 记录 071：再次收敛模块 10 范围，取消当前阶段全部预算相关设计

- 状态：已完成
- 范围：根据最新对齐结果，再次收敛模块 10 当前阶段边界，取消预算相关设计，不再将预算控制作为模块 10 的任务组成部分
- 调整结论：
  - 当前阶段取消：
    - `tiktoken`
    - token 预算统计
    - 字符预算统计
    - 轻量预算对象
    - `max_chunks_per_sub_query / max_total_chunks / max_chars_per_chunk` 之类的预算规则
  - 当前阶段保留：
    - 子任务级 rerank
    - context builder 的结构拼装
    - citation payload
- 当前模块 10 任务拆解同步调整为：
  - 任务 02：实现子任务级 rerank 通道
  - 任务 03：实现 context builder
  - 任务 04：实现 citation payload
  - 任务 05：补本地验收脚本、README 与运行说明
- 调整原因：
  - 当前最重要的是先把后半段主链路打通
  - 预算控制不属于当前必须前置的阻塞项
  - 若现在继续保留预算层，会让 context builder 的实现边界变复杂
- 当前实现原则：
  - context builder 第一阶段只负责：
    - 保留 `sub-query` 边界
    - 组织代表证据
    - 输出稳定上下文结构
  - 不负责预算裁剪策略
- 下一步：
  - 进入模块 10 任务 02：实现子任务级 rerank 通道

#### 记录 068：启动新开发模块，按 `Step 09.4-9.6` 完成检索编排后半段闭环

- 状态：进行中
- 范围：在模块 09 前半段 `9.1 / 9.2 / 9.3` 已完成并通过真实本地验收的基础上，启动下一开发模块，继续完成 `Step 09` 后半段闭环
- 模块定位：
  - 当前新模块不直接进入 `Step 10` 回答生成
  - 当前新模块优先完成：
    - `9.4` 子任务级 `LLM rerank`
    - `9.5` context builder
    - `9.6` citation payload
  - 目标是先让检索编排链路具备“可稳定喂给生成层”的标准输出
- 启动原因：
  - 当前系统已经具备：
    - query decomposition
    - fixed query expansion
    - per-sub-query 四路召回与归并
  - 当前系统仍缺少：
    - 候选集进一步重排
    - 上下文结构拼装
    - 引用载荷结构
  - 若此时直接跳到 `Step 10`，回答层会建立在不稳定的检索输出之上，风险更高
  - 已进一步确认当前模块的关键实现选择为：
    - `9.4 rerank` 采用独立 reranker 通道
    - reranker 模型采用：
      - `Qwen/Qwen3-Reranker-8B`
    - reranker 网关采用：
      - `SiliconFlow`
- 分步任务拆解：
  - 任务 01：检索编排后半段设计对接与当前代码差异修正
    - 对照 `9.4 / 9.5 / 9.6` 与当前实现完成第一轮差异梳理
    - 明确哪些能力进入当前模块，哪些继续留给 `Step 10`
  - 任务 02：实现子任务级 rerank 通道
    - 先只处理单个 `sub-query` 内部候选集
    - 独立于现有 `generate_text` 通道
    - 采用 `SiliconFlow` 上的 `Qwen/Qwen3-Reranker-8B`
  - 任务 03：实现 context builder
    - 按 `sub-query` 边界、代表证据与相邻关系生成最终上下文片段集
  - 任务 04：实现 citation payload
    - 生成面向后续回答层的结构化引用数据
    - 先服务后端生成链路，不急于做前端展示格式
  - 任务 05：补本地验收脚本、README 与运行说明
    - 固化 `Step 09` 完整闭环的真实本地验收入口
- 当前边界判断：
  - 本模块结束标准应是：
    - 输出可直接喂给回答生成层的标准上下文包
  - 本模块不应提前进入：
    - `Step 10` 回答生成
    - 前端交互层
    - 评估闭环
- 当前建议执行顺序：
  - 先完成 `9.4 / 9.5 / 9.6` 与当前实现差异对接
  - 再补独立 rerank 通道
  - 然后补 context builder
  - 最后补 citation payload 与本地验收
- 遗留问题：
  - `SiliconFlow` 的 rerank 接口协议是否与当前 embedding 网关完全同构，需在任务 03 中按真实接口对接
  - `9.6` 的 citation payload 是否直接兼容后续回答层 schema，需在任务 04 中确认
- 下一步：
  - 开始当前模块任务 01：检索编排后半段设计对接与当前代码差异修正

#### 记录 067：完成模块 09 任务 05，补本地验收脚本、README 与运行说明

- 状态：已完成
- 范围：完成模块 09 中“任务 05：补本地验收脚本、README 与运行说明”，为 `Step 09.1-9.3` 前半段提供真实本地验收入口与文档说明
- 结果：
  - 已新增：
    - `scripts/verify_local_step09_orchestration.py`
  - 当前本地验收脚本已串起模块 09 前半段完整链路：
    - 导入一份包含 `Step 8 / Step 9` 内容的 Markdown 样例
    - 执行 query decomposition
    - 对每个 `sub-query` 执行固定三类扩展：
      - `base_query`
      - `step_back_query`
      - `hyde_query`
    - 对每个 `sub-query` 执行四路召回与子任务内归并
    - 输出独立 `sub-query` 结果摘要与 `fused_rrf_score`
  - 已更新 `README.md`，补充：
    - 模块 09 前半段当前能力边界
    - `query_decomposition_service / query_expansion_service / subquery_retrieval_service` 入口说明
    - 最小 Step 09 前半段示例
    - 本地验收脚本运行命令
  - 已更新 `scripts/README.md`，补充 `verify_local_step09_orchestration.py` 脚本说明
  - 已同步补齐本地 `.env` 中缺失的：
    - `LLM_BASE_URL`
    - `LLM_API_KEY`
    - `LLM_MODEL_ID`
    - `LLM_MODEL_MINI_ID`
    - `LLM_EMBEDDING_BASE_URL`
    - `LLM_EMBEDDING_API_KEY`
    - `LLM_EMBEDDING_MODEL_ID`
    - `SYSTEM_MEMORY_MILVUS_URI`
- 验证结果：
  - `python3 -m py_compile scripts/verify_local_step09_orchestration.py` 通过
  - `python3 -m pytest tests/test_retrieval_service.py` 通过
  - 已完成一次真实本地 `Step 09` 前半段验收脚本执行
  - 当前真实返回已确认：
    - `decomposition_mode = decompose`
    - `sub_queries = ["Step 8的职责？", "Step 9的职责？"]`
    - 每个 `sub-query` 都成功生成：
      - `step_back_query`
      - `hyde_query`
    - 每个 `sub-query` 都成功返回独立候选集
    - 顶层候选已返回：
      - `hit_sources`
      - 四路 rank 信息
      - `fused_rrf_score`
- 当前实现边界：
  - 模块 09 的 `9.1 / 9.2 / 9.3` 前半段已形成最小闭环
  - 当前尚未进入：
    - `9.4` 子任务级 LLM rerank
    - `9.5` context builder
    - `9.6` citation payload
    - Step 10 生成链路
- 遗留问题：
  - 当前真实样例中顶层候选主要命中向量三路，`base_bm25` 不保证每次都命中，这属于当前设计允许范围
  - 当前脚本仍是开发验收入口，尚未下沉为 CLI 子命令
- 下一步：
  - 模块 09 前半段已完成，可进入下一开发模块讨论

#### 记录 066：完成模块 09 任务 04，实现单个 `sub-query` 内部 4 路结果归并

- 状态：已完成
- 范围：完成模块 09 中“任务 04：实现单个 `sub-query` 内部 4 路结果归并”，对固定扩展后的单个检索单元执行：
  - `base_query + bm25`
  - `base_query + vector`
  - `step_back_query + vector`
  - `hyde_query + vector`
- 结果：
  - 已在 `src/mindwiki/application/retrieval_models.py` 中新增：
    - `SubQueryCandidate`
    - `SubQueryResult`
  - 已新增 `src/mindwiki/application/subquery_retrieval_service.py`
  - 当前已建立单个 `sub-query` 的独立执行与输出结构：
    - 输入：
      - `sub_query_id`
      - `sub_query_text`
      - `QueryExpansion`
    - 输出：
      - `SubQueryResult`
      - `candidates[]`
  - 当前已按 `Step 9.3` 第一阶段规则实现：
    - 4 路检索执行
    - 按 `chunk_id` 精确去重
    - 保留命中来源：
      - `base_bm25`
      - `base_vector`
      - `step_back_vector`
      - `hyde_vector`
    - 保留各路 rank：
      - `rank_base_bm25`
      - `rank_base_vector`
      - `rank_step_back_vector`
      - `rank_hyde_vector`
    - 按融合版 RRF 计算：
      - `k = 60`
      - `base_bm25 = 0.35`
      - `base_vector = 0.30`
      - `step_back_vector = 0.20`
      - `hyde_vector = 0.15`
  - 当前已明确模块边界：
    - 本任务只输出单个 `sub-query` 的独立候选集
    - 当前仍未进行多个 `sub-query` 间的全局打平
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py` 通过
  - 当前检索相关测试共 `20` 个，全部通过
  - 已新增测试覆盖：
    - 四路结果按 `chunk_id` 合并
    - 融合版 RRF 排序
    - 单个 `sub-query` 执行器按四路顺序调用底层仓储并返回独立候选集
- 当前实现边界：
  - 已完成 `9.1 / 9.2 / 9.3` 的最小代码落地
  - 当前尚未进入：
    - `9.4` 子任务级 rerank
    - `9.5` context builder
    - `9.6` citation payload
    - Step 10 生成链路
- 遗留问题：
  - 当前新能力仍是独立服务，尚未补统一本地验收脚本和 README 入口
  - 当前尚未把“query decomposition -> query expansion -> sub-query retrieval”串成完整模块 09 前半段演示链路
- 下一步：
  - 进入模块 09 任务 05：补本地验收脚本、README 与运行说明

#### 记录 065：完成模块 09 任务 03，建立固定三类查询扩展服务

- 状态：已完成
- 范围：完成模块 09 中“任务 03：实现固定三类查询扩展”，对原 query 或每个 `sub-query` 建立固定 `base_query / step_back_query / hyde_query` 输出结构
- 结果：
  - 已在 `src/mindwiki/application/retrieval_models.py` 中新增：
    - `QueryExpansion`
  - 已新增 `src/mindwiki/application/query_expansion_service.py`
  - 已建立模块 09 第一阶段固定扩展输出结构：
    - `base_query`
    - `step_back_query`
    - `hyde_query`
    - `use_step_back`
    - `use_hyde`
  - 当前 `QueryExpansionService.expand()` 已按模块 09 设计落地最小实现：
    - `base_query` 直接保留当前检索单元
    - `step_back_query` 通过现有 LLM service 生成
    - `hyde_query` 通过现有 LLM service 生成
  - 当前已通过结构化 JSON schema 约束 LLM 输出：
    - `step_back_query`
    - `hyde_query`
  - 当前已明确第一阶段行为：
    - 每个检索单元固定只生成 `1` 条 `step_back_query`
    - 每个检索单元固定只生成 `1` 条 `hyde_query`
    - 默认：
      - `use_step_back = true`
      - `use_hyde = true`
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py` 通过
  - 当前检索相关测试共 `17` 个，全部通过
  - 已新增测试覆盖：
    - 固定扩展正常生成 `base_query / step_back_query / hyde_query`
    - LLM 扩展失败时抛出错误，避免静默回落为不可信扩展
- 当前实现边界：
  - 本任务只完成 `9.2` 固定三类扩展服务
  - 当前尚未进入：
    - `9.3` 单个 `sub-query` 四路结果归并
    - `9.4` 子任务级 rerank
    - `9.5` context builder
  - 当前扩展服务仍是独立能力，下一步需要接入统一检索编排层
- 遗留问题：
  - 当前 `step_back_query` 与 `hyde_query` 还未进入真实召回执行链路
  - 当前尚未建立“一个 `sub-query` 输出一组独立候选集”的编排结果结构
- 下一步：
  - 进入模块 09 任务 04：实现单个 `sub-query` 内部 4 路结果归并

#### 记录 064：完成模块 09 任务 02，建立 query decomposition 协议与规则优先最小实现

- 状态：已完成
- 范围：完成模块 09 中“任务 02：建立 query decomposition 协议与最小实现”，先以规则优先方式落地 `Step 9.1`
- 结果：
  - 已在 `src/mindwiki/application/retrieval_models.py` 中新增：
    - `QueryDecomposition`
  - 已建立模块 09 第一阶段拆解输出协议：
    - `decomposition_mode = none | decompose`
    - `sub_queries[]`
    - `reason`
  - 已新增 `src/mindwiki/application/query_decomposition_service.py`
  - 当前已落地第一版规则优先拆解服务：
    - `QueryDecompositionService.decompose()`
  - 当前规则覆盖的最小场景包括：
    - 比较类
    - 多对象总结类
    - 一问多点类
  - 当前已正式固化第一阶段约束：
    - 默认只允许一层拆解
    - `sub_queries` 最多 `3` 条
    - 无法稳定拆解时优先返回：
      - `decomposition_mode = none`
  - 当前实现已显式避免错误拆解的场景：
    - 后续子句依赖代词时不拆
    - 回顾梳理类当前先保守保留整体 query，不提前做激进拆分
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py` 通过
  - 已新增测试覆盖：
    - 单主题 query 默认不拆
    - 比较类 query 拆解
    - 多对象总结类 query 拆解
    - 一问多点类 query 拆解
    - 代词依赖场景保持不拆
- 当前实现边界：
  - 本任务只完成 `9.1` 的协议与规则优先最小实现
  - 当前尚未接入：
    - `9.2` `base_query / step_back_query / hyde_query`
    - `9.3` 单个 `sub-query` 四路归并
  - 当前也尚未把 LLM 判定正式引入拆解链路，避免在模块 09 前半段过早扩大不确定性
- 遗留问题：
  - 后续若规则命中率不足，可在不改变输出协议的前提下补 LLM 辅助判定
  - 当前 `QueryDecompositionService` 仍是独立编排服务，后续需要在任务 03 进入统一检索编排入口
- 下一步：
  - 进入模块 09 任务 03：实现固定三类查询扩展

#### 记录 063：完成模块 09 任务 01，补检索编排设计对接与当前代码差异修正

- 状态：已完成
- 范围：完成模块 09 中“任务 01：检索编排设计对接与当前代码差异修正”，对照 `Step 9.1 / 9.2 / 9.3` 与当前已落地检索代码，收敛模块 09 的真实开发边界与实现缺口
- 对照结论：
  - 已核对设计文档：
    - `doc/design/step-09-retrieval-orchestration/09.01-query-decomposition-rules.md`
    - `doc/design/step-09-retrieval-orchestration/09.02-step-back-and-hyde-expansion-strategy.md`
    - `doc/design/step-09-retrieval-orchestration/09.03-subquery-local-merge-strategy.md`
  - 已核对当前实现：
    - `src/mindwiki/application/retrieval_models.py`
    - `src/mindwiki/application/retrieval_service.py`
  - 已确认当前代码实际只覆盖：
    - 单查询输入
    - `bm25_only`
    - `vector_only`
    - `hybrid`
  - 已确认当前代码尚未进入模块 09 正式范围的能力包括：
    - `9.1` query decomposition 协议
    - `decomposition_mode = none | decompose`
    - `sub_queries[]`
    - `9.2` 固定三类扩展：
      - `base_query`
      - `step_back_query`
      - `hyde_query`
    - `9.3` 单个 `sub-query` 四路归并：
      - `base_query + bm25`
      - `base_query + vector`
      - `step_back_query + vector`
      - `hyde_query + vector`
    - `9.3` 子任务级独立候选集输出结构
- 当前差异修正结果：
  - 已确认当前 `RetrievalQuery` 仍是单一 `query` 输入模型，不能直接承接 `sub_queries[]`
  - 已确认当前 `RetrievalResult` 仍是单层 `hits[]` 输出，不能表达“每个 `sub-query` 独立候选集”
  - 已确认当前 `hybrid` 只是：
    - 原始 query 的两路召回归并
    - `bm25 + vector`
  - 已确认当前 `hybrid` 不是 `9.3` 所要求的四路归并实现
  - 已确认当前融合逻辑仍沿用模块 08 的通用混合召回打分，不等同于 `9.3` 中面向单个 `sub-query` 的融合版 RRF 权重方案
- 模块 09 后续实现边界已正式收敛为：
  - 任务 02：建立 `9.1` 拆解协议与最小实现
  - 任务 03：建立 `9.2` 固定三类扩展结构
  - 任务 04：建立 `9.3` 单个 `sub-query` 四路归并结构
  - 任务 05：补模块 09 前半段本地验收脚本与说明
- 明确不纳入本模块当前阶段的内容：
  - `9.4` 子任务级 LLM rerank
  - `9.5` context builder
  - `9.6` citation payload
  - Step 10 生成链路
- 遗留问题：
  - 模块 09 需要先补新的编排输入输出模型，再决定如何最小侵入接入现有 `RetrievalService`
  - 模块 08 的 `hybrid` 应继续保留为底层召回能力，不应直接替代模块 09 的编排层输出结构
- 下一步：
  - 进入模块 09 任务 02：建立 query decomposition 协议与最小实现

#### 记录 062：修正模块 09 方向，按 `Step 9.1-9.3` 推进检索编排前半段

- 状态：已完成
- 范围：在模块 08 已完成 `bm25_only / vector_only / hybrid` 检索基础与本地验收闭环的前提下，重新对齐 `Step 9` 设计稿，修正下一开发模块的目标、边界与任务拆解
- 结果：
  - 已确认此前对模块 09 的定义偏离了 `Step 9` 设计稿正式线路
  - 已重新核对 `9.1 / 9.2 / 9.3` 设计稿后确认：
    - `9.1` 负责 query 拆解
    - `9.2` 负责对原 query 或每个 `sub-query` 固定生成：
      - `base_query`
      - `step_back_query`
      - `hyde_query`
    - `9.3` 负责单个 `sub-query` 内部 4 路结果归并
  - 已确认模块 09 当前阶段不应提前进入：
    - `9.4` 子任务级 LLM rerank
    - `9.5` context builder
    - `9.6` citation payload
    - Step 10 生成链路
  - 已确认模块 09 的前置基础已经具备：
    - `bm25_only`
    - `vector_only`
    - `hybrid`
    - import-time embedding 与 `Milvus` 写入
    - 统一 `ChunkHit` 返回结构
- 模块目标：
  - 让系统第一次具备符合 `Step 9` 设计稿的检索编排前半段能力
  - 先完成：
    - query decomposition
    - step-back / HyDE 扩展
    - 单个 `sub-query` 内部 4 路结果归并
  - 为后续 `9.4 / 9.5 / 9.6 / Step 10` 提供稳定输入
- 分步任务拆解：
  - 任务 01：检索编排设计对接与当前代码差异修正
    - 对照 `9.1 / 9.2 / 9.3` 与当前实现完成第一轮差异梳理
    - 明确哪些能力进入模块 09，哪些继续留到后续 `9.4+`
  - 任务 02：建立 query decomposition 协议与最小实现
    - 顶层输出：
      - `decomposition_mode = none | decompose`
    - 若为 `decompose`，输出：
      - `sub_queries[]`
  - 任务 03：实现固定三类查询扩展
    - 对原 query 或每个 `sub-query` 固定生成：
      - `base_query`
      - `step_back_query`
      - `hyde_query`
  - 任务 04：实现单个 `sub-query` 内部 4 路结果归并
    - `base_query + bm25`
    - `base_query + vector`
    - `step_back_query + vector`
    - `hyde_query + vector`
    - 按设计稿中的融合版 RRF 完成子任务内归并
  - 任务 05：补本地验收脚本、README 与运行说明
    - 固化模块 09 前半段的本地验收入口
    - 补最小示例与当前能力边界说明
- 当前建议执行顺序：
  - 先完成设计与当前实现差异对接
  - 再补 query decomposition
  - 然后补固定三类扩展
  - 最后补单个 `sub-query` 内 4 路结果归并与本地验收
- 当前边界判断：
  - 模块 08 已经把候选召回层补完整，不需要在模块 09 重复实现底层检索
  - 当前最缺的是符合设计稿的编排前半段，而不是直接进入 context builder 或生成层
  - 直接跳 `9.4+` 或 Step 10 会让后续链路建立在缺失 query 规划和单子任务归并的基础上，风险更高
- 遗留问题：
  - `9.1` 的拆解判断具体是规则优先还是直接走 LLM 判定，需在任务 02 讨论时收敛
  - `9.2` 的 `step_back_query / hyde_query` 是否直接复用现有 `generate_text` 能力，需在任务 03 中正式确定
  - `9.3` 的 4 路结果归并是否在本模块就对接现有 `hybrid` 检索 service，需在任务 04 中收口
- 下一步：
  - 开始模块 09 任务 01：检索编排设计对接与当前代码差异修正

#### 记录 061：完成模块 08 任务 06，补本地 `hybrid` 验收脚本、README 与运行说明

- 状态：已完成
- 范围：完成模块 08 中“任务 06：补本地 `hybrid` 验收脚本、README 与运行说明”
- 结果：
  - 已新增 `scripts/verify_local_hybrid_retrieval.py`
  - 已为 `hybrid` 模块补充第一版本地验收脚本能力：
    - 导入一份带标签的 Markdown 样例
    - 依赖导入时自动完成 embedding 生成与 `Milvus` 写入
    - 执行一轮宽范围 `hybrid` 检索
    - 执行一轮带 `tags / source_types / document_scope / time_range` 的过滤检索
    - 校验导入文档可以在两类混合查询下被命中
    - 校验返回中包含：
      - `vector_score`
      - `bm25_score`
      - `rrf_score`
      - `final_score`
  - 已更新 `README.md`，补充：
    - `hybrid` 当前能力边界
    - 最小 `hybrid` 调用示例
    - 混合检索本地验收命令
  - 已更新 `scripts/README.md`，补充 `verify_local_hybrid_retrieval.py` 的脚本说明
  - 当前模块 08 已具备从 `bm25_only / vector_only` 到 `hybrid` 融合召回与本地验收脚本的最小闭环
- 验证结果：
  - `python3 -m py_compile scripts/verify_local_hybrid_retrieval.py` 通过
  - 已完成一次真实本地 `hybrid` 验收脚本执行
  - 当前真实返回已覆盖：
    - `vector_score`
    - `bm25_score`
    - `rrf_score`
    - `final_score`
- 遗留问题：
  - 当前尚未进入 rerank
  - 当前尚未进入 Step 09 编排层
  - 当前 `hybrid` 本地验收脚本仍依赖真实 embedding 网关与真实 `Milvus`
- 下一步：
  - 模块 08 已完成，可进入下一开发模块讨论

#### 记录 060：完成模块 08 任务 05，补 `score_breakdown` 与排序打平规则

- 状态：已完成
- 范围：完成模块 08 中“任务 05：补 `score_breakdown` 与排序打平规则”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_service.py`
  - 当前 `hybrid` 返回中的 `score_breakdown` 已正式补齐第一阶段核心字段：
    - `vector_score`
    - `bm25_score`
    - `rrf_score`
    - `normalized_rrf_score`
    - `normalized_vector_score`
    - `normalized_bm25_score`
    - `dual_hit_bonus`
    - `final_score`
  - 当前 `ChunkHit.score` 在 `hybrid` 模式下仍保持：
    - `score = final_score`
  - 已将第一阶段排序打平规则明确固化到测试中：
    - 先按 `final_score`
    - 再按：
      - `dual_hit_bonus`
      - `normalized_rrf_score`
      - `normalized_vector_score`
      - `normalized_bm25_score`
  - 当前 `hybrid` 的返回结构已更接近 `Step 8.7 / 8.8` 的验证需求：
    - 可直接观察两路原始分数
    - 可直接观察融合分数与双命中奖励
    - 可直接辅助后续本地调试与人工判断
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_embedding_service.py tests/test_vector_index_service.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_cli.py tests/test_llm_models.py` 通过
  - 当前共 `60` 个测试，全部通过
  - 已新增测试覆盖：
    - `hybrid` 返回完整 `score_breakdown`
    - 排序打平规则按设计稿顺序生效
- 遗留问题：
  - 当前还没有真实本地 `hybrid` 端到端联调
  - 当前还没有固定的 `hybrid` 本地验收脚本和 README 运行命令
- 下一步：
  - 进入模块 08 任务 06：补本地 `hybrid` 验收脚本、README 与运行说明

#### 记录 059：完成模块 08 任务 04，扩展统一检索 service，接入 `hybrid`

- 状态：已完成
- 范围：完成模块 08 中“任务 04：扩展统一检索 service，接入 `hybrid`”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_service.py`
  - 当前统一检索 service 已支持三种模式：
    - `bm25_only`
    - `vector_only`
    - `hybrid`
  - 当前 `hybrid` 检索链路已按以下顺序工作：
    - 执行 `search_bm25()`
    - 执行 `search_vector()`
    - 按 `chunk_id` 合并两路候选
    - 执行 `RRF + 加权融合`
    - 取前 `top_k` 条结果并映射为统一 `ChunkHit`
  - 已在 `HybridCandidate` 中补最小 `match_sources` 承接：
    - 当前会合并：
      - `vector`
      - BM25 命中来源字段，例如 `section_title / chunk_text`
  - 当前 `hybrid` 对外返回已收敛为：
    - `score = final_score`
    - `match_sources` 为两路命中来源的合并结果
    - `score_breakdown` 当前最小先承接：
      - `final_score`
  - 当前实现边界保持收敛：
    - 本任务只完成 `hybrid` 对外编排接入
    - 尚未把完整融合中间分数字段全部透传到 `score_breakdown`
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_embedding_service.py tests/test_vector_index_service.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_cli.py tests/test_llm_models.py` 通过
  - 当前共 `59` 个测试，全部通过
  - 已新增测试覆盖：
    - `hybrid` 模式同时调用两路仓储
    - `hybrid` 返回 `final_score`
    - `hybrid` 返回合并后的 `match_sources`
- 遗留问题：
  - 当前 `score_breakdown` 仍未补全：
    - `vector_score`
    - `bm25_score`
    - `rrf_score`
    - `normalized_rrf_score`
    - `normalized_vector_score`
    - `normalized_bm25_score`
    - `dual_hit_bonus`
  - 当前还没有真实本地 `hybrid` 端到端联调与固定验收脚本
- 下一步：
  - 进入模块 08 任务 05：补 `score_breakdown` 与排序打平规则

#### 记录 058：完成模块 08 任务 03，实现 `hybrid` 去重、RRF 与加权融合

- 状态：已完成
- 范围：完成模块 08 中“任务 03：实现 `hybrid` 去重、RRF 与加权融合”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_service.py`
  - 已新增第一版纯函数化融合算法：
    - `score_hybrid_candidates()`
  - 当前融合算法已正式落地 `Step 8.7` 第一阶段规则：
    - RRF 固定常数：
      - `k = 60`
    - `rrf_score = vector_rrf_part + bm25_rrf_part`
    - `min-max normalization`
    - `dual_hit_bonus`
    - `final_score`
  - 当前已按设计稿实现以下细节：
    - rank 从 `1` 开始
    - 未命中的通道分数记 `0`
    - 若某一路所有值相同，则该列统一归一化为 `1.0`
    - `final_score` 采用：
      - `0.50 * normalized_rrf_score`
      - `0.20 * normalized_vector_score`
      - `0.20 * normalized_bm25_score`
      - `0.10 * dual_hit_bonus`
  - 当前混合排序已按以下规则稳定输出：
    - 先按 `final_score` 降序
    - 同分时再按：
      - `dual_hit_bonus`
      - `normalized_rrf_score`
      - `normalized_vector_score`
      - `normalized_bm25_score`
  - 当前 `HybridCandidate` 在本任务后已可承接完整融合中间态：
    - `rrf_score`
    - `normalized_rrf_score`
    - `normalized_vector_score`
    - `normalized_bm25_score`
    - `dual_hit_bonus`
    - `final_score`
  - 当前实现边界保持收敛：
    - 本任务只完成融合算法本身
    - 尚未将 `hybrid` 接入 `RetrievalService.retrieve()`
    - 尚未将完整融合结果映射为最终 `ChunkHit`
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_embedding_service.py tests/test_vector_index_service.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_cli.py tests/test_llm_models.py` 通过
  - 当前共 `58` 个测试，全部通过
  - 已新增测试覆盖：
    - `RRF + 加权融合` 结果
    - 单通道缺失时归一化记 `0`
    - 某一列全等值时归一化记 `1.0`
    - `final_score` 排序顺序
- 遗留问题：
  - 当前 `hybrid` 仍未对外暴露
  - 当前 `ChunkHit.score_breakdown` 还没有承接完整融合字段
  - 当前还没有真实本地 `hybrid` 端到端联调
- 下一步：
  - 进入模块 08 任务 04：扩展统一检索 service，接入 `hybrid`

#### 记录 057：完成模块 08 任务 02，扩展候选模型与融合中间结构

- 状态：已完成
- 范围：完成模块 08 中“任务 02：扩展候选模型与融合中间结构”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_models.py`
  - 已新增：
    - `HybridCandidate`
  - 当前 `HybridCandidate` 已能承接第一阶段混合检索融合前所需的中间字段：
    - `chunk_id`
    - `projection`
    - `vector_hit`
    - `bm25_hit`
    - `vector_score`
    - `bm25_score`
    - `rank_vector`
    - `rank_bm25`
    - 以及后续任务 03 需要继续填充的：
      - `rrf_score`
      - `normalized_rrf_score`
      - `normalized_vector_score`
      - `normalized_bm25_score`
      - `dual_hit_bonus`
      - `final_score`
  - 已扩展 `src/mindwiki/application/retrieval_service.py`
  - 已新增纯内存候选合并逻辑：
    - `merge_hybrid_candidates()`
  - 当前合并逻辑已正式按 `chunk_id` 合并两路候选：
    - `vector_candidates`
    - `bm25_candidates`
  - 当前合并逻辑的最小行为已收敛为：
    - 记录双路是否命中
    - 记录各自原始分数
    - 记录各自通道 rank，且 rank 从 `1` 开始
    - 为后续任务 03 的 `RRF + 加权融合` 提供稳定输入
  - 当前实现边界保持收敛：
    - 本任务只补中间结构与候选合并
    - 尚未开始计算：
      - `rrf_score`
      - 各类归一化分数
      - `dual_hit_bonus`
      - `final_score`
    - 尚未将 `hybrid` 真正接入 `RetrievalService.retrieve()`
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_embedding_service.py tests/test_vector_index_service.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_cli.py tests/test_llm_models.py` 通过
  - 当前共 `56` 个测试，全部通过
  - 已新增测试覆盖：
    - 双路命中按 `chunk_id` 合并
    - 单路命中保留
    - `rank_vector / rank_bm25` 的稳定记录
- 遗留问题：
  - 当前 `HybridCandidate` 仍未填充融合公式相关字段值
  - 当前尚未定义 `normalized_*` 的边界处理实现
  - 当前 `hybrid` 还不能对外提供真实检索结果
- 下一步：
  - 进入模块 08 任务 03：实现 `hybrid` 去重、RRF 与加权融合

#### 记录 056：完成模块 08 任务 01，混合检索设计对接与当前代码差异修正

- 状态：已完成
- 范围：完成模块 08 中“任务 01：混合检索设计对接与当前代码差异修正”
- 结果：
  - 已对照 `Step 8.5 / 8.6 / 8.7 / 8.8` 与当前代码结构完成第一轮差异梳理
  - 已确认当前实现与模块 08 目标一致的基础部分：
    - 检索主对象仍统一为 `chunk`
    - 当前已存在统一检索输入：
      - `RetrievalQuery`
      - `RetrievalFilters`
    - 当前已存在统一检索输出：
      - `ChunkHit`
      - `RetrievalResult`
    - 当前强过滤在两条单通道中都已具备可落地基础：
      - `tags`
      - `source_types`
      - `document_scope`
      - `time_range`
    - 当前两条基础召回通道都已真实存在：
      - `bm25_only`
      - `vector_only`
    - 当前统一检索 service 已具备承接第三种 `retrieval_mode = hybrid` 的稳定外壳
  - 已确认当前实现与 `Step 8.5 / 8.6 / 8.7 / 8.8` 存在的主要差异：
    - `RetrievalQuery.retrieval_mode` 当前默认值仍是：
      - `bm25_only`
      - 与设计稿中的默认 `hybrid` 尚未对齐
    - 当前 `RetrievalService` 还没有：
      - 同时执行 BM25 与向量召回
      - 两路候选去重合并
      - `hybrid` 最终排序
    - 当前仓储层虽然分别具备：
      - `search_bm25()`
      - `search_vector()`
      - 但尚未具备：
        - 统一 `hybrid` 候选合并结构
        - `rank_vector`
        - `rank_bm25`
        - 双路命中标记
    - 当前统一返回结构中的 `score_breakdown` 只覆盖单通道最小值：
      - `bm25_score`
      - `vector_score`
      - 尚未承接：
        - `rrf_score`
        - `normalized_rrf_score`
        - `normalized_vector_score`
        - `normalized_bm25_score`
        - `dual_hit_bonus`
        - `final_score`
    - 当前尚未落实 `Step 8.6` 中建议的内部召回参数分层：
      - `vector_top_k = 30`
      - `bm25_top_k = 30`
      - 现在两条单通道仍主要直接复用接口层 `top_k`
    - 当前尚未落实 `Step 8.7` 中的：
      - 按 `chunk_id` 合并候选
      - `k = 60` 的 RRF 固定常数
      - `0.50 / 0.20 / 0.20 / 0.10` 融合权重
      - 同分打破规则
    - 当前还没有 `Step 8.8` 要求的本地 `hybrid` 验收样例与固定验证脚本
  - 已正式确认模块 08 第一阶段应按以下边界继续推进：
    - 任务 02 负责补融合中间结构与候选合并字段
    - 任务 03 负责实现 `RRF + 加权融合`
    - 任务 04-05 再接入统一 service 与完整 `score_breakdown`
    - 任务 06 最后补 `hybrid` 本地验收脚本与 README
  - 已明确当前不应在模块 08 任务 01 中提前并入：
    - rerank
    - query decomposition
    - step-back
    - HyDE
    - context builder
    - Step 09 编排
- 代码对接结论：
  - `src/mindwiki/application/retrieval_models.py` 当前仍缺少专门承接两路合并与融合排序的中间结构
  - `src/mindwiki/infrastructure/retrieval_repository.py` 目前只负责单通道查询，`hybrid` 不应简单拼接两路结果，而应引入显式融合步骤
  - `src/mindwiki/application/retrieval_service.py` 当前是最合适承接 `hybrid` 编排的位置，但需要先有稳定的融合输入结构
  - 当前 README 与脚本说明已经能够反映单通道现状，后续需在 `hybrid` 完成后同步更新
- 遗留问题：
  - `RetrievalQuery.retrieval_mode` 是否在模块 08 完成后立即改为默认 `hybrid`，还是先保留显式传参兼容期，需在任务 04 中收敛
  - `normalized_*` 的全等值边界处理需在任务 03 中明确写成代码与测试
  - 本地 `hybrid` 验收样例需兼顾：
    - 标题词
    - 标签词
    - 正文词
    - 语义改写
    - 范围过滤
- 下一步：
  - 进入模块 08 任务 02：扩展候选模型与融合中间结构

#### 记录 055：确定模块 08 为混合检索与融合排序 MVP

- 状态：进行中
- 范围：在模块 07 已完成 import-time embedding、`Milvus` 写入、`vector_only` 与 `bm25_only` 单通道召回的前提下，正式定义下一开发模块的目标、边界与任务拆解
- 结果：
  - 已确认模块 08 的核心目标是：
    - 先补齐 `hybrid` 检索与融合排序的最小闭环
  - 已确认模块 08 当前阶段不直接进入：
    - LLM rerank
    - query decomposition
    - step-back
    - HyDE
    - sub-query merge
    - context builder
    - Step 09 完整检索编排
  - 已确认模块 08 主要覆盖范围：
    - 对齐 `Step 8.5 / 8.6 / 8.7 / 8.8` 与当前代码结构
    - 在统一检索 service 中接入 `retrieval_mode = hybrid`
    - 建立两路候选按 `chunk_id` 去重与合并逻辑
    - 落地第一阶段 `RRF + 加权融合` 公式
    - 扩展统一 `score_breakdown`
    - 补本地 `hybrid` 验收脚本与 README 说明
  - 已确认模块 08 的实现主对象仍统一为：
    - `chunk`
  - 已确认模块 08 的输出仍保持复用统一 `chunk hit` 协议，但需补充：
    - `bm25_score`
    - `vector_score`
    - `rrf_score`
    - `normalized_rrf_score`
    - `normalized_vector_score`
    - `normalized_bm25_score`
    - `dual_hit_bonus`
    - `final_score`
- 模块目标：
  - 让系统第一次具备可解释的双通道混合召回能力
  - 保持与现有强过滤、`ChunkHit` 返回结构和后续 Step 09 编排层兼容
  - 为后续 rerank、context builder 和问答生成链路提供更稳定候选集
- 分步任务拆解：
  - 任务 01：混合检索设计对接与当前代码差异修正
    - 对照 `Step 8.5 / 8.6 / 8.7 / 8.8` 与当前代码完成第一轮差异梳理
    - 明确哪些能力进入模块 08，哪些继续留到后续 Step 09 / Step 10
  - 任务 02：扩展候选模型与融合中间结构
    - 补两路候选合并所需字段
    - 补统一融合候选结构与排序辅助字段
  - 任务 03：实现 `hybrid` 去重、RRF 与加权融合
    - 按 `chunk_id` 合并两路候选
    - 计算 `rrf_score`
    - 计算归一化分数
    - 计算 `dual_hit_bonus`
    - 计算 `final_score`
  - 任务 04：扩展统一检索 service，接入 `hybrid`
    - 在现有 `bm25_only / vector_only` 基础上补 `hybrid`
    - 保持现有模式兼容
  - 任务 05：补 `score_breakdown` 与排序打平规则
    - 对齐 `Step 8.7` 的返回字段
    - 对齐同分时的稳定排序规则
  - 任务 06：补本地 `hybrid` 验收脚本、README 与运行说明
    - 固化混合检索的本地验收入口
    - 补最小示例与能力边界说明
- 当前建议执行顺序：
  - 先完成设计与当前实现差异对接
  - 再补融合中间结构
  - 然后落 `RRF + 加权融合`
  - 最后补统一返回和本地验收
- 当前边界判断：
  - 模块 07 已解决 import-time vector 写入与 `vector_only` 单通道召回，不需要在模块 08 重复实现
  - `hybrid` 是进入 Step 09 编排层之前最关键的检索层缺口
  - 当前如果直接跳到 Step 09 或 Step 10，会建立在不完整的候选集能力之上
- 遗留问题：
  - `normalized_vector_score / normalized_bm25_score` 的边界处理需在任务 03 中明确落地
  - `vector_top_k / bm25_top_k` 是否继续先复用接口层 `top_k`，还是引入内部默认值，需在任务 01 中收敛
  - 本地 `hybrid` 验收脚本仍会依赖真实 embedding 网关、PostgreSQL 与真实 `Milvus`
- 下一步：
  - 开始模块 08 任务 01：混合检索设计对接与当前代码差异修正

#### 记录 054：完成模块 07 任务 07，补本地 `vector_only` 验收脚本与运行说明

- 状态：已完成
- 范围：完成模块 07 中“任务 07：补本地验收脚本、README 与运行说明”
- 结果：
  - 已新增 `scripts/verify_local_vector_retrieval.py`
  - 已为 `vector_only` 模块补充第一版本地验收脚本能力：
    - 导入一份带标签的 Markdown 样例
    - 依赖导入时自动完成 embedding 生成与 `Milvus` 写入
    - 执行一轮宽范围 `vector_only` 检索
    - 执行一轮带 `tags / source_types / document_scope / time_range` 的过滤检索
    - 校验导入文档可以在两类向量查询下被命中
    - 校验返回中包含：
      - `match_sources = ("vector",)`
      - `score_breakdown.vector_score`
  - 已更新 `README.md`，补充：
    - `vector_only` 当前能力边界
    - 最小 `vector_only` 调用示例
    - 向量检索本地验收命令
  - 已更新 `scripts/README.md`，补充 `verify_local_vector_retrieval.py` 的脚本说明
  - 当前模块 07 已具备从 import-time embedding、`Milvus` 写入到 `vector_only` 召回与本地验收脚本的最小闭环
- 验证结果：
  - `python3 -m py_compile scripts/verify_local_vector_retrieval.py` 通过
  - 已完成一次真实本地 `vector_only` 检索验证，命中 `Vector Smoke Note`
- 遗留问题：
  - 当前尚未实现 `hybrid`
  - 当前尚未实现 RRF、多路融合和 rerank
  - 当前向量本地验收脚本仍依赖真实 embedding 网关与真实 `Milvus`
- 下一步：
  - 模块 07 已完成，可进入下一开发模块讨论

#### 记录 053：完成模块 07 任务 05-06，实现 `vector_only` 检索仓储与统一 service 接入

- 状态：已完成
- 范围：完成模块 07 中“任务 05：实现 `vector_only` 检索仓储与候选映射”“任务 06：扩展统一检索 service，接入 `vector_only`”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_models.py`
  - 已新增：
    - `VectorCandidate`
  - 已扩展 `src/mindwiki/infrastructure/milvus_store.py`
  - 已新增 `search_chunk_vectors()`：
    - 基于 query embedding 执行 `Milvus` 向量检索
    - 默认过滤：
      - `is_active = true`
      - `embedding_version = v1`
    - 支持按候选 `chunk_id` 集合约束 `Milvus` 搜索范围
  - 已扩展 `src/mindwiki/infrastructure/retrieval_repository.py`
  - 已建立第一版统一检索仓储组合能力：
    - PostgreSQL 继续负责 BM25 与 chunk 投影
    - embedding service 负责查询向量生成
    - `Milvus` 负责 `vector_only` 相似检索
  - 当前 `vector_only` 检索链路已按以下顺序工作：
    - 先根据 `tags / source_types / document_scope / time_range` 在 PostgreSQL 中筛出可参与向量检索的 `chunk_id`
    - 对 query 生成 embedding
    - 在 `Milvus` 中执行向量搜索
    - 回到 PostgreSQL 取回统一 `chunk projection`
    - 映射为统一 `chunk hit`
  - 已扩展 `src/mindwiki/application/retrieval_service.py`
  - 当前统一检索 service 已支持：
    - `bm25_only`
    - `vector_only`
  - 当前 `vector_only` 命中结果已统一收敛为：
    - `match_sources = ("vector",)`
    - `score_breakdown = {"vector_score": <score>}`
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_embedding_service.py tests/test_vector_index_service.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_cli.py tests/test_llm_models.py` 通过
  - 当前共 `54` 个测试，全部通过
  - 已完成一次真实本地 `vector_only` 检索验证：
    - 检索模式返回 `vector_only`
    - 命中 `Vector Smoke Note`
    - 返回 `vector_score`
    - 标签过滤 `vector-smoke` 生效
- 遗留问题：
  - 当前尚未实现 `hybrid`
  - 当前尚未实现多路融合、RRF 和 rerank
  - 当前还没有单独的本地 `vector_only` 验收脚本
- 下一步：
  - 进入模块 07 任务 07：补本地验收脚本、README 与运行说明

#### 记录 052：完成模块 07 任务 02-04，打通 embedding 与 `Milvus` 最小写入闭环

- 状态：已完成
- 范围：完成模块 07 中“任务 02：补 embedding 输入构造与版本字段承接”“任务 03：接入 `Milvus` 配置、客户端与 collection schema”“任务 04：实现 chunk 向量写入、失效与重建承接”
- 结果：
  - 已新增 embedding 相关配置承接：
    - `LLM_EMBEDDING_BASE_URL`
    - `LLM_EMBEDDING_API_KEY`
    - `LLM_EMBEDDING_MODEL_ID`
    - `LLM_EMBEDDING_TIMEOUT_MS`
  - 已新增 `Milvus` 相关配置承接：
    - `SYSTEM_MEMORY_MILVUS_URI`
    - `SYSTEM_MEMORY_MILVUS_TOKEN`
    - `MILVUS_COLLECTION_NAME`
  - 已新增 `src/mindwiki/llm/embedding_models.py`
  - 已新增 `src/mindwiki/llm/embedding_service.py`
  - 已基于现有 OpenAI-compatible 风格 provider 扩展 embedding 调用能力：
    - 通过 `/embeddings` 生成批量向量
    - 第一阶段采用 OpenAI-compatible embedding provider
  - 已新增 `src/mindwiki/infrastructure/vector_index_repository.py`
  - 已新增 `src/mindwiki/infrastructure/milvus_store.py`
  - 已新增 `src/mindwiki/application/vector_index_service.py`
  - 已正式落地 `Step 8.3` 第一阶段 embedding 输入模板：
    - `document_title`
    - 可选 `section_title`
    - `chunk_text`
    - 固定模板：
      - `Document Title: ...`
      - `Section Title: ...`
      - `Content:`
  - 已正式落地第一阶段 embedding 元数据字段：
    - `embedding_ref`
    - `embedding_provider`
    - `embedding_model`
    - `embedding_version`
    - `embedding_dim`
  - 当前第一阶段 embedding version 已收敛为：
    - `v1`
  - 已扩展 `scripts/init_local_db.sql`，为 `chunks` 表补齐 embedding 元数据列
  - 已将 import 成功后的最小向量写入链路挂入 `ImportService`：
    - PostgreSQL 落库成功后按 `document_id` 拉取 chunk
    - 批量生成 embedding
    - 以 `chunk_id` 作为稳定 `embedding_ref`
    - 写入 `Milvus`
    - 将 embedding 元数据回写 PostgreSQL
  - 当前文档重导入时，已在写入新向量前执行同文档旧向量删除
  - 当前如果 embedding 或 `Milvus` 未配置，导入链路会显式输出：
    - `vector_sync=skipped`
    - `vector_reason=embedding_or_milvus_not_configured`
- 验证结果：
  - `python3 -m pytest tests/test_embedding_service.py tests/test_vector_index_service.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_cli.py tests/test_llm_models.py` 通过
  - 当前共 `53` 个测试，全部通过
  - 当前已完成代码级最小验证：
    - embedding provider 请求与响应解析
    - embedding service 组装请求
    - 向量索引 service 的输入拼接、Milvus 写入与 PostgreSQL 元数据回写
- 遗留问题：
  - 当前尚未完成 `vector_only` 检索路径
  - 当前尚未完成本地端到端向量验收脚本
  - 当前未完成真实本地联调：
    - 本地 `Milvus` 在本次环境探测中未连通
    - 本次沙箱内 PostgreSQL TCP 直连也未放通
- 下一步：
  - 进入模块 07 任务 05：实现 `vector_only` 检索仓储与候选映射

#### 记录 051：完成模块 07 任务 01，向量检索设计对接与当前代码差异修正

- 状态：已完成
- 范围：完成模块 07 中“任务 01：向量检索设计对接与当前代码差异修正”
- 结果：
  - 已对照 `Step 8.1 / 8.2 / 8.3 / 8.5 / 8.6` 与当前代码结构完成第一轮差异梳理
  - 已确认当前实现与模块 07 目标一致的基础部分：
    - 检索主对象仍统一为 `chunk`
    - 当前已存在统一检索输入：
      - `RetrievalQuery`
      - `RetrievalFilters`
    - 当前已存在统一检索输出：
      - `ChunkHit`
      - `RetrievalResult`
    - 当前已存在最小强过滤承接能力：
      - `tags`
      - `source_types`
      - `document_scope`
      - `time_range`
    - 当前 `time_range` 第一阶段语义已正式收敛为：
      - `documents.imported_at`
    - 当前 `RetrievalService` 与 PostgreSQL 检索仓储已提供后续接入 `vector_only` 的稳定外壳
  - 已确认当前实现与 `Step 8` 存在的主要差异：
    - `RetrievalService` 当前仅支持：
      - `bm25_only`
    - 当前仓储层仅实现：
      - PostgreSQL BM25 检索
    - 当前不存在任何：
      - `Milvus` 客户端
      - `Milvus` 配置项
      - `Milvus` collection / record schema
      - 向量写入
      - 向量删除或失效处理
      - `vector_only` 查询路径
    - 当前数据库 schema 中仅保留了：
      - `chunks.embedding_ref`
      - 但尚未保留：
        - `embedding_provider`
        - `embedding_model`
        - `embedding_version`
        - `embedding_dim`
    - 当前导入落库链路只会写入 `chunks.embedding_ref = NULL`
    - 当前系统尚无任何真实 embedding 生成入口：
      - LLM 模块当前只暴露 `generate_text`
      - 尚无独立 embedding service / provider 协议
    - 当前尚未实现 `Step 8.3` 规定的 embedding 输入拼接：
      - `document_title`
      - `section_title`
      - `chunk_text`
    - 当前统一返回结构中的 `score_breakdown` 仍只承接：
      - `bm25_score`
  - 已正式确认模块 07 第一阶段应按以下边界继续推进：
    - 任务 02 负责补 embedding 输入构造与版本字段承接
    - 任务 03 负责补 `Milvus` 配置、客户端与 collection schema
    - 任务 04 负责补向量写入、失效与重建承接
    - 任务 05-06 再进入 `vector_only` 仓储与 service 接入
  - 已明确当前不应在本模块任务 01 中提前并入：
    - `hybrid`
    - `RRF`
    - rerank
    - Step 09 编排
- 代码对接结论：
  - `src/mindwiki/application/retrieval_models.py` 已具备承接统一 `vector_only` 返回结构的基础，但仍需补充向量候选模型或统一映射来源
  - `src/mindwiki/application/retrieval_service.py` 目前对非 `bm25_only` 会直接拒绝，后续需在保持兼容的前提下扩展 `vector_only`
  - `src/mindwiki/infrastructure/retrieval_repository.py` 当前是 PostgreSQL 专用实现，后续需新增 `Milvus` 检索仓储而不是在现有 BM25 SQL 中混写
  - `src/mindwiki/infrastructure/settings.py` 当前无任何 `Milvus` 环境配置项
  - `scripts/init_local_db.sql` 与 `src/mindwiki/infrastructure/import_repository.py` 当前只承接 `embedding_ref` 占位，尚不足以支撑版本化向量链路
- 遗留问题：
  - `embedding` 生成是继续复用现有 LLM provider 体系扩展，还是建立独立最小 embedding provider 协议，仍需在任务 02-03 之间收敛
  - `Milvus` 的本地连接参数、collection 命名和过滤字段集合仍需在任务 03 中正式确定
  - 导入链路是否在模块 07 第一阶段就默认执行自动向量写入，仍需在任务 04 中进一步收口
- 下一步：
  - 进入模块 07 任务 02：补 embedding 输入构造与版本字段承接

#### 记录 050：确定模块 07 为 `Milvus` 向量检索基础模块 MVP

- 状态：进行中
- 范围：在模块 06 已完成 `bm25_only` 基础召回、向量库选型已切换为 `Milvus` 的前提下，正式定义下一开发模块的目标、边界与任务拆解
- 结果：
  - 已确认模块 07 的核心目标是：
    - 先补齐 `embedding + Milvus + vector_only` 的最小闭环
  - 已确认模块 07 当前阶段不直接进入：
    - `hybrid` 融合排序
    - `RRF` / 多路融合公式
    - LLM rerank
    - query decomposition
    - context builder
    - Step 09 完整检索编排
  - 已确认模块 07 主要覆盖范围：
    - 对齐 `Step 8.1 / 8.2 / 8.3 / 8.5 / 8.6` 与当前代码结构
    - 补 embedding 输入构造与版本字段承接
    - 接入 `Milvus` 客户端与最小配置项
    - 建立 `Milvus` collection / record schema 与写入删除能力
    - 实现 `vector_only` 最小召回链路
    - 补本地验收脚本与 README 说明
  - 已确认模块 07 的实现主对象仍统一为：
    - `chunk`
  - 已确认模块 07 的第一阶段返回目标仍保持与模块 06 一致：
    - 继续复用统一 `chunk hit` 协议
    - 在已有 `score_breakdown` 上补 `vector_score`
- 模块目标：
  - 让系统第一次具备真实的语义向量写入与向量召回能力
  - 保持与现有 `RetrievalService`、过滤条件和 `chunk hit` 返回结构兼容
  - 为后续 `hybrid` 与 Step 09 编排层提供稳定向量通道
- 分步任务拆解：
  - 任务 01：向量检索设计对接与当前代码差异修正
    - 对照 `Step 8.1 / 8.2 / 8.3 / 8.5 / 8.6` 与当前代码完成第一轮差异梳理
    - 明确 embedding 输入来源、版本字段落点、Milvus 写入边界和 `vector_only` 返回目标
    - 明确哪些能力进入模块 07，哪些继续留到后续 `hybrid / Step 09`
  - 任务 02：补 embedding 输入构造与版本字段承接
    - 建立统一 embedding 输入构造函数
    - 第一阶段按 `document_title + section_title + chunk_text` 承接输入拼接
    - 在本地数据结构中补齐 `embedding_provider / embedding_model / embedding_version / embedding_dim / embedding_ref`
  - 任务 03：接入 `Milvus` 配置、客户端与 collection schema
    - 增加本地配置项与环境变量约定
    - 封装 `Milvus` 客户端创建逻辑
    - 明确 collection 名称、主键字段、vector 字段和标量过滤字段
  - 任务 04：实现 chunk 向量写入、失效与重建承接
    - 基于现有 chunk 数据生成向量写入 payload
    - 支持单文档重建时的旧向量失效或删除
    - 为后续导入链路自动写入预留稳定入口
  - 任务 05：实现 `vector_only` 检索仓储与候选映射
    - 建立 `Milvus` 查询仓储
    - 承接 `tags / source_types / time_range / document_scope` 的前置过滤
    - 将向量检索结果映射到统一候选结构，并补 `vector_score`
  - 任务 06：扩展统一检索 service，接入 `vector_only`
    - 在 `RetrievalService` 中接入 `vector_only`
    - 保持与现有 `bm25_only` 行为兼容
    - 为后续 `hybrid` 预留稳定 service 入口
  - 任务 07：补本地验收脚本、README 与运行说明
    - 增加 `Milvus` 本地验收脚本
    - 补环境配置、启动方式和验证命令
    - 在 README 中明确当前只完成 `vector_only`，尚未进入 `hybrid`
- 当前建议执行顺序：
  - 先完成设计与当前实现差异对接
  - 再补 embedding 输入与版本字段
  - 然后接 `Milvus` 客户端与写入链路
  - 最后打通 `vector_only` 检索与本地验收
- 当前边界判断：
  - 模块 06 已解决 `bm25_only` 与强过滤基础，不需要在模块 07 重复实现
  - `hybrid` 依赖向量召回先稳定落地，因此不应与模块 07 同步并入
  - Step 09 的编排能力依赖 `bm25_only + vector_only` 两条通道先稳定存在，因此也不应提前进入
- 遗留问题：
  - 当前项目仍未接入任何真实 embedding 生成链路用于检索
  - 当前项目仍未声明 `Milvus` 本地连接配置、collection 命名和验收命令
  - 模块 07 是否一次承接导入链路中的自动向量写入，需在任务 04 讨论时进一步收敛
- 下一步：
  - 开始模块 07 任务 01：向量检索设计对接与当前代码差异修正

#### 记录 049：确认向量库选型切换为 `Milvus`

- 状态：进行中
- 范围：根据当前本地环境与最新决策，修正设计稿和后续模块 07 的向量存储选型
- 结果：
  - 已确认当前向量库选型由 `Qdrant` 调整为 `Milvus`
  - 已同步修正 `Step 4` 存储与索引设计中的向量库表述
  - 已同步修正 `Step 5` 导入错误分类、重试说明与导入流程文案中的向量索引表述
  - 已同步修正路线图中的向量存储方案说明
  - 已明确模块 07 后续应围绕 `Milvus` 落地：
    - embedding 元数据与版本字段
    - `Milvus` collection / record 结构
    - 向量写入、删除与重建
    - `vector_only` 最小召回链路
- 说明：
  - `记录 048` 反映的是切换前基于既有设计稿的核对结果
  - 当前正式有效的后续实现方向，以本记录中的 `Milvus` 选型为准
- 遗留问题：
  - 当前项目里仍未接入 `Milvus` 客户端、配置项与本地验收脚本
  - 现有模块 07 任务拆分仍需按 `Milvus` 版本重新细化
- 下一步：
  - 基于 `Milvus` 重新定义模块 07，并先落第一个向量基础设施子任务

#### 记录 048：修正模块 07 方向，向量基础设施以 `Qdrant` 为准

- 状态：进行中
- 范围：核对既有设计稿中向量存储选型，并修正后续开发模块的承接方向
- 结果：
  - 已重新核对 `Step 4` 与 `Step 8` 设计稿
  - 已确认当前设计稿中的向量数据库正式选型为：
    - `Qdrant`
  - 已确认以下设计结论已经明确写入文档：
    - `PostgreSQL` 作为主数据源
    - `Qdrant` 承担 `Chunk` 级语义检索向量索引
    - `BM25` 承担关键词全文检索
    - 向量索引主对象为 `chunk`
    - 向量检索相关版本字段包括：
      - `embedding_provider`
      - `embedding_model`
      - `embedding_version`
      - `embedding_dim`
  - 已确认模块 06 仅完成 `bm25_only` 基础召回，尚未实现：
    - embedding 生成
    - `Qdrant` 写入
    - `vector_only`
    - `hybrid`
  - 基于设计稿与当前实现差异，后续模块 07 应优先承接：
    - embedding 输入与版本字段落地
    - `Qdrant` collection / point / payload 结构落地
    - 向量写入与删除同步
    - `vector_only` 最小召回链路
  - 模块 07 暂不应直接定义为 `Step 9` 编排层
- 设计依据：
  - `doc/design/step-04-storage-design/04.01-storage-layer-mapping.md`
  - `doc/design/step-04-storage-design/04.03-index-and-incremental-update-strategy.md`
  - `doc/design/step-08-index-and-retrieval/08.02-embedding-generation-and-versioning-strategy.md`
- 遗留问题：
  - 当前项目中尚未接入 `Qdrant` 客户端与本地验收链路
  - 模块 07 仍需进一步拆成可逐步交付的子任务
- 下一步：
  - 基于 `Qdrant` 重新定义模块 07 的任务拆分，并先从向量基础设施开始

#### 记录 047：完成模块 06 任务 07，补本地验收脚本与 README 说明

- 状态：已完成
- 范围：完成模块 06 中“任务 07：补本地验收脚本与 README 说明”
- 结果：
  - 已新增 `scripts/verify_local_retrieval.py`
  - 已为基础检索模块补充第一版本地验收脚本能力：
    - 导入一份带标签的 Markdown 样例
    - 执行一轮宽范围 `bm25_only` 检索
    - 执行一轮带 `tags / source_types / document_scope / time_range` 的过滤检索
    - 校验导入文档可以在两类查询下被命中
    - 输出统一 JSON 摘要，包含：
      - `broad_top_hit`
      - `tagged_top_hit`
      - `match_sources`
      - `score_breakdown`
  - 已更新 `README.md`，补充：
    - 当前检索模块能力边界
    - `bm25_only` 检索说明
    - 强过滤条件说明
    - 最小检索调用示例
    - 检索本地验收命令
  - 已更新 `scripts/README.md`，补充 `verify_local_retrieval.py` 的脚本说明
  - 当前模块 06 已具备从标签/时间承接、投影、BM25、统一 `chunk hit` 到本地验收脚本的最小闭环
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_cli.py tests/test_llm_models.py tests/test_llm_provider.py tests/test_llm_service.py` 通过
  - `python3 -m py_compile scripts/verify_local_retrieval.py` 通过
  - 真实执行 `PYTHONPATH=src python3 scripts/verify_local_retrieval.py` 成功
  - 本次真实返回：
    - `import_exit_code = 0`
    - `broad_hit_count = 5`
    - `tagged_hit_count = 1`
    - `broad_top_hit.document_title = Retrieval Verification Note`
    - `tagged_top_hit.source_type = markdown`
- 遗留问题：
  - 当前检索仍只支持 `bm25_only`
  - 当前还没有 CLI 形式的检索入口
  - 当前还没有 `vector_only / hybrid`、LLM rerank、context builder
- 下一步：
  - 模块 06 已完成，可进入下一开发模块讨论

#### 记录 046：完成模块 06 任务 06，实现统一 `chunk hit` 返回结构与最小过滤能力

- 状态：已完成
- 范围：完成模块 06 中“任务 06：实现统一 `chunk hit` 返回结构与最小过滤能力”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_models.py`
  - 已新增统一检索结果模型：
    - `ChunkHit`
    - `RetrievalResult`
  - 已新增 `src/mindwiki/application/retrieval_service.py`
  - 已建立第一版上层检索 service：
    - `RetrievalService`
    - 统一 `retrieve()` 入口
  - 当前 `retrieve()` 已完成的最小行为包括：
    - 承接 `RetrievalQuery`
    - 当前仅允许 `retrieval_mode = bm25_only`
    - 调用检索仓储执行 `search_bm25()`
    - 将 BM25 候选统一映射为 `chunk hit`
  - 当前统一 `chunk hit` 已收敛为：
    - `chunk_id`
    - `document_id`
    - `section_id`
    - `document_title`
    - `section_title`
    - `chunk_text`
    - `source_type`
    - `location`
    - `score`
    - `match_sources`
    - `score_breakdown`
  - 当前最小过滤能力已从“SQL 可承接”推进到“上层可调用”：
    - `source_types`
    - `document_scope`
    - `tags`
    - `time_range`
  - 当前 `score_breakdown` 第一阶段先保留最小兼容结构：
    - `{"bm25_score": <score>}`
  - 当前实现边界仍保持收敛：
    - 尚未进入 `vector_only`
    - 尚未进入 `hybrid`
    - 尚未接入 CLI 或本地检索验收脚本
  - 已新增 `tests/test_retrieval_service.py`，覆盖：
    - BM25 候选到 `chunk hit` 的统一映射
    - 强过滤条件透传到仓储层
    - 非 `bm25_only` 模式的拒绝行为
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_service.py tests/test_retrieval_projection.py tests/test_cli.py tests/test_llm_models.py tests/test_llm_provider.py tests/test_llm_service.py` 通过
  - 当前共 `49` 个测试，全部通过
- 遗留问题：
  - 当前检索能力还没有本地端到端验收脚本
  - 当前 README 还未说明检索层用法与当前限制
  - 当前尚未提供可直接手工触发的检索入口
- 下一步：
  - 进入模块 06 任务 07：补本地验收脚本与 README 说明

#### 记录 045：完成模块 06 任务 05，实现基础关键词 / BM25 召回 MVP

- 状态：已完成
- 范围：完成模块 06 中“任务 05：实现基础关键词 / BM25 召回 MVP”
- 结果：
  - 已扩展 `src/mindwiki/application/retrieval_models.py`
  - 已新增第一版检索输入与候选模型：
    - `RetrievalQuery`
    - `BM25Candidate`
  - 已扩展 `src/mindwiki/infrastructure/retrieval_repository.py`
  - 已建立第一版 PostgreSQL 原生全文检索 BM25 MVP 能力：
    - `search_bm25()`
    - `build_bm25_query()`
  - 当前 BM25 MVP 已采用 PostgreSQL 原生全文检索承接关键词召回：
    - 使用 `websearch_to_tsquery('simple', query)`
    - 使用 `ts_rank_cd(...)` 作为基础相关性分数
    - 在查询层直接完成 `bm25_score > 0` 过滤
  - 当前已按 `Step 8.4` 的优先级承接加权字段：
    - `document_title` -> `A`
    - `section_title` -> `B`
    - `document_tags` -> `C`
    - `chunk_text` -> `D`
  - 当前已建立最小 `match_sources` 承接基础：
    - `document_title`
    - `section_title`
    - `document_tags`
    - `chunk_text`
  - 当前 BM25 查询已复用前置强过滤能力：
    - `source_types`
    - `document_scope`
    - `tags`
    - `time_range`
  - 当前实现边界仍保持收敛：
    - 尚未进入 `vector_only`
    - 尚未进入 `hybrid`
    - 尚未实现完整 `chunk hit` 返回对象
    - 尚未引入更复杂的融合或重排逻辑
  - 已扩展 `tests/test_retrieval_projection.py`，覆盖：
    - BM25 查询中的加权 `tsvector`
    - `websearch_to_tsquery` 使用
    - `bm25_score` 过滤与排序
    - 前置过滤参数与 BM25 参数的联合组装
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_projection.py tests/test_cli.py tests/test_llm_models.py tests/test_llm_provider.py tests/test_llm_service.py` 通过
  - 当前共 `46` 个测试，全部通过
- 遗留问题：
  - 当前 BM25 候选尚未被统一包装成正式 `chunk hit`
  - 当前还没有上层检索 service 对 `search_bm25()` 的调用封装
  - 当前还没有本地检索验收脚本
- 下一步：
  - 进入模块 06 任务 06：实现统一 `chunk hit` 返回结构与最小过滤能力

#### 记录 044：完成模块 06 任务 04，补最小检索数据投影

- 状态：已完成
- 范围：完成模块 06 中“任务 04：补最小检索数据投影”
- 结果：
  - 已新增 `src/mindwiki/application/retrieval_models.py`
  - 已建立第一版检索侧共享模型：
    - `TimeRange`
    - `RetrievalFilters`
    - `ChunkLocation`
    - `ChunkProjection`
  - 已新增 `src/mindwiki/infrastructure/retrieval_repository.py`
  - 已建立第一版 PostgreSQL 检索投影仓储能力：
    - `ProjectionQuery`
    - `RetrievalRepository`
    - `PostgresRetrievalRepository`
    - `build_projection_query()`
    - `build_retrieval_repository()`
  - 当前最小检索数据投影已覆盖：
    - `chunk_id`
    - `document_id`
    - `section_id`
    - `document_title`
    - `section_title`
    - `chunk_text`
    - `source_type`
    - `document_type`
    - `document_tags`
    - `location.chunk_index`
    - `location.section_id`
    - `location.page_number`
    - `location.imported_at`
  - 当前投影查询已具备前置过滤承接能力：
    - `source_types`
    - `document_scope`
    - `tags`
    - `time_range`
  - 当前实现边界保持收敛：
    - 本任务只补投影与过滤查询承接
    - 尚未进入关键词匹配 / BM25 排序逻辑
    - 尚未生成统一 `chunk hit` 结果
  - 已新增 `tests/test_retrieval_projection.py`，覆盖：
    - 无过滤条件时的最小投影 SQL
    - 多过滤条件同时生效时的 SQL 与参数组装
- 验证结果：
  - `python3 -m pytest tests/test_retrieval_projection.py tests/test_cli.py tests/test_llm_models.py tests/test_llm_provider.py tests/test_llm_service.py` 通过
  - 当前共 `44` 个测试，全部通过
- 遗留问题：
  - 当前检索投影仓储尚未被上层召回服务消费
  - 当前还没有关键词匹配、排序分数与 `match_sources`
- 下一步：
  - 进入模块 06 任务 05：实现基础关键词 / BM25 召回 MVP

#### 记录 043：完成模块 06 任务 03，明确第一阶段 `time_range` 时间字段承接

- 状态：已完成
- 范围：完成模块 06 中“任务 03：明确并补第一阶段 `time_range` 时间字段承接”
- 结果：
  - 已正式确定模块 06 第一阶段的 `time_range` 承接字段为：
    - `documents.imported_at`
  - 已正式确定第一阶段 `time_range` 的语义为：
    - 导入时间过滤
    - 表示文档进入 MindWiki 的时间范围
  - 已明确第一阶段当前不承诺以下时间语义：
    - 文档原始创建时间
    - 文档原始发布时间
    - 事件发生时间
    - 笔记内容中的业务时间
  - 已确认采用 `documents.imported_at` 的原因：
    - 当前数据库已存在该字段
    - 无需新增新的时间抽取与解析链路
    - 过滤行为稳定、可解释、可立即落地
    - 不会阻塞后续模块 06 的 BM25 与统一检索接口实现
  - 已确认第一阶段 `time_range` 的实现边界：
    - 支持基于导入时间的范围过滤
    - 文档说明中需明确这是“导入时间”，不是“文档原始时间”
    - 若后续需要真实文档时间语义，应在后续模块中单独扩展字段与提取链路
- 遗留问题：
  - 当前尚未进入检索实现，因此 `time_range` 过滤逻辑本身会在后续任务中接入查询层
  - 后续若希望支持更真实的文档时间语义，需要新字段和明确来源策略
- 下一步：
  - 进入模块 06 任务 04：补最小检索数据投影

#### 记录 042：完成模块 06 任务 02，补标签真实落库与检索侧承接

- 状态：已完成
- 范围：完成模块 06 中“任务 02：补标签真实落库与检索侧承接”
- 结果：
  - 已更新 `scripts/init_local_db.sql`，新增：
    - `tags`
    - `document_tags`
  - 已更新 `scripts/reset_local_db.sql`，补充标签相关表的清理顺序
  - 已更新 `src/mindwiki/infrastructure/import_repository.py`，让 Markdown / PDF 导入成功后把 `request.tags` 真实写入：
    - `tags.tag_name`
    - `document_tags.document_id -> tag_id`
  - 当前标签落库行为已收敛为：
    - 标签按名称去重
    - 同一文档与同一标签关系按 `(document_id, tag_id)` 去重
    - 导入请求中的标签不再只停留在 `input_payload`
    - 后续检索层已具备承接 `document_tags` 的正式数据基础
  - 已扩展 `tests/test_cli.py` 中的 recording repository 断言，补充导入链路对标签持久化承接的回归保护
- 验证结果：
  - `python3 -m pytest tests/test_cli.py tests/test_llm_models.py tests/test_llm_provider.py tests/test_llm_service.py` 通过
  - 当前共 `42` 个测试，全部通过
- 遗留问题：
  - 当前标签虽已真实落库，但检索侧尚未开始消费 `document_tags`
  - 当前尚未补真实数据库级标签回查或本地验收脚本
- 下一步：
  - 进入模块 06 任务 03：明确并补第一阶段 `time_range` 时间字段承接

#### 记录 041：调整模块 06 范围，将 `tags` 与 `time_range` 前置能力插入任务拆解

- 状态：进行中
- 范围：根据最新对齐结果，调整模块 06 的任务拆解，不再把 `tags` 过滤与 `time_range` 过滤完全后置，而是将其前置依赖显式纳入模块 06
- 结果：
  - 已确认模块 06 若希望支持：
    - `tags` 过滤
    - `time_range` 过滤
    则必须先补对应前置能力，而不能直接在召回层做伪实现
  - 已确认新的插入原则：
    - `tags`：先补标签真实落库，再进入过滤与命中能力
    - `time_range`：先明确第一阶段时间语义，再进入过滤实现
  - 已确认模块 06 的任务拆解调整为：
    - 任务 01：检索设计对接与当前数据结构差异修正
    - 任务 02：补标签真实落库与检索侧承接
    - 任务 03：明确并补第一阶段 `time_range` 时间字段承接
    - 任务 04：补最小检索数据投影
    - 任务 05：实现基础关键词 / BM25 召回 MVP
    - 任务 06：实现统一 `chunk hit` 返回结构与最小过滤能力
    - 任务 07：补本地验收脚本与 README 说明
- 当前调整后的实现原则：
  - `tags` 过滤不再跳过，而是先补真实数据基础后再做
  - `time_range` 第一阶段不再悬空，而是要求先明确是否采用 `documents.imported_at` 作为正式承接字段
  - 模块 06 仍然只承接 `Step 8` 的基础召回层，不跨入 `Step 9`
- 遗留问题：
  - `time_range` 第一阶段是否最终采用 `documents.imported_at`，仍需在具体任务中明确写入
- 下一步：
  - 进入模块 06 任务 02：补标签真实落库与检索侧承接

#### 记录 040：完成模块 06 任务 01，检索设计对接与当前数据结构差异修正

- 状态：已完成
- 范围：完成模块 06 中“任务 01：检索设计对接与当前数据结构差异修正”
- 结果：
  - 已对照 `Step 8.1 / 8.4 / 8.5 / 8.6` 与当前数据库结构、导入落库逻辑完成第一轮对接
  - 已确认当前实现与 `Step 8` 一致的基础部分：
    - 检索主对象可统一收敛为 `chunk`
    - 当前已具备 `documents / sections / chunks / sources` 四层最小关联结构
    - `document_title` 可由 `documents.title` 承接
    - `section_title` 可由 `sections.title` 承接
    - `chunk_text` 可由 `chunks.content_text` 承接
    - `source_type` 可由 `documents.document_type` 或 `sources.source_type` 承接
    - `document_scope` 过滤具备可落地数据基础
    - `source_types` 过滤具备可落地数据基础
    - PDF 已具备最小 `page_number` 定位承接
  - 已确认当前实现与 `Step 8` 存在的主要差异：
    - `document_tags` 尚未真实落库，因此本模块第一阶段不能把 `tags` 过滤或 `document_tags` 命中当作已实现能力
    - 当前没有任何 embedding 数据、向量索引或版本管理能力，因此 `vector_only / hybrid` 暂不能进入模块 06 的真实交付范围
    - 当前没有 `bm25_score / vector_score / rrf_score` 等分数字段承接，因此 `score_breakdown` 第一阶段只能先保留最小兼容位
    - Markdown 仍未落 `line_start / line_end`，因此 `location` 目前只能先提供最小版本：
      - Markdown：先保留 `section_id / chunk_index`
      - PDF：可额外提供 `page_number`
    - `time_range` 目前只有 `documents.imported_at` 可作为近似字段，尚未有更明确的文档时间语义来源
  - 基于上述对齐，已确认模块 06 第一阶段的实现边界：
    - 优先实现：
      - 标签真实落库与检索侧承接
      - 第一阶段 `time_range` 字段语义收敛
      - 基础关键词 / BM25 召回
      - 统一 `chunk hit` 返回结构
      - `source_types` 过滤
      - `document_scope` 过滤
      - 最小 `location` 承接
    - 暂不承诺：
      - `vector_only`
      - `hybrid`
      - 完整 `score_breakdown`
      - query planning / rerank / context builder
  - 已确认模块 06 当前建议返回字段可先收敛为：
    - `chunk_id`
    - `document_id`
    - `section_id`
    - `document_title`
    - `section_title`
    - `chunk_text`
    - `source_type`
    - `location`
    - `score`
    - `match_sources`
- 设计对接结论：
  - `8.1` 的“统一以 chunk 为主对象”可以直接承接
  - `8.4` 中 `document_title / section_title / chunk_text` 的命中能力可先落，`document_tags` 暂不进入
  - `8.5` 的统一接口可以先做 `bm25_only` 的最小实现，并把 `retrieval_mode` 其余分支留待后续模块
  - `8.6` 的“召回前过滤”原则可以先在 `source_types / document_scope` 上落地
- 遗留问题：
  - `tags` 过滤已决定纳入模块 06，但需先补标签真实落库
  - `time_range` 已决定纳入模块 06，但需先明确第一阶段时间语义
  - 若后续希望支持 `hybrid`，仍需先补 embedding、向量存储与召回路径
  - 若后续希望支持更细粒度 citation `location`，仍需补 Markdown 行号级定位
- 下一步：
  - 进入模块 06 任务 02：补标签真实落库与检索侧承接

#### 记录 039：确定模块 06 为基础检索与候选召回 MVP

- 状态：进行中
- 范围：将下一个开发模块正式定义为“基础检索与候选召回 MVP”，优先承接 `Step 8` 的基础召回层，不把 `Step 9` 的检索编排一次性并入同一模块
- 结果：
  - 已确认模块 06 的核心目标是先把“稳定召回 chunk 候选”这件事落地
  - 已确认模块 06 当前阶段不直接进入：
    - query decomposition
    - step-back
    - HyDE
    - sub-query merge
    - LLM rerank
    - context builder
    - citation payload
  - 已确认模块 06 主要覆盖范围：
    - 对齐 `Step 8` 与当前数据结构差异
    - 补最小检索数据投影
    - 实现基础关键词 / BM25 召回 MVP
    - 实现统一 `chunk hit` 返回结构
    - 实现最小过滤能力
    - 补本地验收脚本与 README 说明
    - 为后续模块 07 的 `Step 9` 编排层预留接口
  - 已确认模块拆分原则：
    - 模块 06 负责“召回”
    - 模块 07 再负责“编排与 LLM 检索增强”
- 当前边界判断：
  - `Step 9` 依赖 `Step 8` 先有稳定候选集
  - 当前虽然已完成 LLM 模块，但检索主链路仍未真实落地
  - 因此下一步应先完成基础检索层，而不是直接进入编排层
- 遗留问题：
  - `tags` 过滤是否进入模块 06，仍取决于是否先补标签真实落库
  - 若不补标签落库，本模块第一阶段应先只做 `source_types / document_scope` 等可稳定落地的过滤条件
- 下一步：
  - 开始模块 06 任务 01：检索设计对接与当前数据结构差异修正

### 2026-04-29

#### 记录 038：完成模块 05 任务 07，补 README、本地配置说明与验收脚本

- 状态：已完成
- 范围：完成模块 05 中“任务 07：补 README、本地配置说明与验收脚本”
- 结果：
  - 已新增 `scripts/verify_local_llm.py`
  - 已为 LLM 模块补充第一版本地验收脚本能力：
    - 支持读取 `LLM_BASE_URL`
    - 支持读取 `LLM_API_KEY`
    - 支持读取 `LLM_MODEL_ID`
    - 支持通过命令行参数覆盖配置
    - 通过真实 `generate_text` 调用执行 smoke test
    - 校验返回文本是否为 `MINDWIKI_LLM_OK`
    - 输出统一 JSON 摘要，包含 `status / model / usage / validation / error`
  - 已更新 `README.md`，补充：
    - 当前 LLM 模块能力边界
    - `LLM_*` 配置项说明
    - `generate_text` 最小使用示例
    - LLM 本地验收命令
  - 已更新 `scripts/README.md`，补充 `verify_local_llm.py` 的脚本说明
  - 当前模块 05 已具备从配置、provider、service、生命周期控制、结构化校验到本地验收脚本的最小闭环
- 验证结果：
  - `python3 -m pytest tests/test_llm_service.py tests/test_llm_provider.py tests/test_llm_models.py tests/test_cli.py` 通过
  - `python3 -m py_compile scripts/verify_local_llm.py` 通过
  - 真实执行 `PYTHONPATH=src python3 scripts/verify_local_llm.py --base-url https://kuaipao.ai/v1 --api-key <masked> --model gpt-5.4` 成功
  - 本次真实返回：
    - `status = success`
    - `model = gpt-5.4`
    - `output_text = MINDWIKI_LLM_OK`
    - `finish_reason = stop`
    - `usage.total_tokens = 55`
- 遗留问题：
  - 当前仍未实现 citation validation
  - 当前仍未实现结构化 repair 重试
  - 当前 LLM 能力还仅覆盖 `generate_text`
- 下一步：
  - 模块 05 已完成，可进入下一开发模块讨论

#### 记录 037：完成模块 05 任务 06，补结构化输出校验与返回约定

- 状态：已完成
- 范围：完成模块 05 中“任务 06：补结构化输出校验与返回约定”
- 结果：
  - 已扩展 `src/mindwiki/llm/service.py`，让 `generate_text` 在 provider 成功返回后进入本地结构化校验流程
  - 当前已落地的结构化输出承接包括：
    - 透传并保留 `protocol_validation`
    - 对 `response_format.type = json_schema` 的返回执行本地解析
    - 支持最小本地轻修复：
      - 去除 Markdown 代码块包裹后再尝试 JSON 解析
    - 成功解析后写入 `parsed_output`
    - 基于最小 schema 规则执行本地校验
  - 当前已实现的 schema 校验能力包括：
    - JSON 是否可解析
    - `type=object`
    - `type=array`
    - `type=string`
    - `type=number`
    - `type=integer`
    - `type=boolean`
    - `required` 字段缺失检查
    - `properties` 子字段递归校验
    - `items` 数组元素递归校验
  - 当前返回约定已收敛为：
    - 校验通过：
      - `status = success`
      - `validation.final_status = accepted`
      - `parsed_output` 可直接供上层消费
    - 校验失败：
      - `status = failed`
      - `error.error_type = schema_validation_failed`
      - `validation.final_status = repairable`
      - `schema_validation.issues[]` 返回问题清单
  - 当前仍保持边界收敛：
    - 尚未实现 citation 证据集校验
    - 尚未实现结构化 repair 重试
    - 尚未引入完整 JSON Schema 引擎
  - 已更新 `src/mindwiki/llm/models.py`，放宽 `parsed_output` 为通用结构化对象承接
  - 已扩展 `tests/test_llm_service.py`，覆盖：
    - JSON schema 成功解析
    - 无法解析 JSON 的失败路径
    - 必填字段缺失与类型不匹配的失败路径
- 验证结果：
  - `python3 -m pytest tests/test_llm_service.py tests/test_llm_provider.py tests/test_llm_models.py tests/test_cli.py` 通过
  - 当前共 `42` 个测试，全部通过
- 遗留问题：
  - 当前还没有 citation validation
  - 当前还没有 repair 调用链
  - 当前 README 和本地验收脚本尚未补齐
- 下一步：
  - 进入模块 05 任务 07：补 README、本地配置说明与验收脚本

#### 记录 036：完成模块 05 任务 05，补调用生命周期控制与失败处理

- 状态：已完成
- 范围：完成模块 05 中“任务 05：补调用生命周期控制与失败处理”
- 结果：
  - 已升级 `src/mindwiki/llm/service.py`，让 `generate_text` 服务层开始真正承接调用生命周期控制
  - 当前已落地的生命周期能力包括：
    - 为每次请求稳定生成或继承 `request_id`
    - 为每次实际调用生成 `attempt_id`
    - 记录 `retry_count`
    - 标记 `is_fallback`
    - 支持 `max_retries`
    - 支持 `overall_deadline_ms`
    - 在主模型失败后，按条件切换到 mini 模型 fallback
  - 当前重试行为已收敛为：
    - 仅对 `response.error.retryable = true` 的失败执行重试
    - `max_retries = N` 时，总尝试次数为 `N + 1`
    - 不对不可重试错误继续重试
  - 当前 fallback 行为已收敛为：
    - 仅当主模型失败且 `allow_fallback = true` 时触发
    - 仅当失败结果本身允许 fallback 时触发
    - 当前 fallback 目标为 `LLM_MODEL_MINI_ID`
    - fallback 阶段不再继续递归 fallback
  - 当前 deadline 行为已落地为：
    - 每轮尝试前检查是否超过 `overall_deadline_ms`
    - 超过后直接返回 `deadline_exceeded`
    - 不再继续执行后续重试或 fallback
  - `build_llm_service()` 当前已支持同时装配：
    - 主 provider：`LLM_MODEL_ID`
    - fallback provider：`LLM_MODEL_MINI_ID`
  - 已扩展 `tests/test_llm_service.py`，覆盖：
    - 重试成功路径
    - fallback 成功路径
    - deadline 提前失败路径
    - `attempt_id / retry_count / is_fallback` 元数据承接
- 验证结果：
  - `python3 -m pytest tests/test_llm_service.py tests/test_llm_provider.py tests/test_llm_models.py tests/test_cli.py` 通过
  - 当前共 `39` 个测试，全部通过
- 遗留问题：
  - 当前还没有取消机制
  - 当前还没有结构化输出 repair 流程
  - 当前还没有 README 和本地验收脚本说明
- 下一步：
  - 进入模块 05 任务 06：补结构化输出校验与返回约定

### 2026-04-28

#### 记录 035：完成模块 05 任务 04，实现 `generate_text` 最小可用链路

- 状态：已完成
- 范围：完成模块 05 中“任务 04：实现 `generate_text` 最小可用链路”
- 结果：
  - 已新增 `src/mindwiki/llm/service.py`
  - 已建立第一版 `generate_text` 服务入口：
    - `GenerateTextInput`
    - `LLMService`
    - `build_llm_service()`
  - 当前 `generate_text` 已支持的最小能力包括：
    - 将 `system_prompt + user_prompt` 组装为统一 `LLMRequest`
    - 自动补齐 `request_id`
    - 自动写入 `interface_name=generate_text`
    - 承接 `task_type`
    - 承接 `model`
    - 承接 `temperature / top_p / max_tokens`
    - 承接 `response_format`
    - 承接 `max_retries / allow_fallback`
    - 未显式传入时，从 settings 读取 `LLM_TIMEOUT_MS`
    - 通过默认 provider 装配 `OpenAI-compatible /chat/completions` 适配器
  - 已新增 `tests/test_llm_service.py`，覆盖：
    - `generate_text` 请求装配
    - 默认超时读取
    - settings 驱动的默认 service/provider 装配
  - 当前 `generate_text` 已不再只是协议或 provider 级占位，而是形成了真实可调用的服务入口
- 验证结果：
  - `python3 -m pytest tests/test_llm_models.py tests/test_llm_provider.py tests/test_llm_service.py tests/test_cli.py` 通过
  - 当前共 `36` 个测试，全部通过
  - 已使用真实配置完成一次最小模型调用验证：
    - `LLM_BASE_URL = https://kuaipao.ai/v1`
    - `LLM_MODEL_ID = gpt-5.4`
    - 返回 `status = success`
    - 返回 `output_text = MINDWIKI_LLM_OK`
    - `finish_reason = stop`
    - `usage.total_tokens = 55`
- 遗留问题：
  - 当前还没有统一的重试循环和 fallback 生命周期控制
  - 当前还没有结构化输出 schema 校验与 repair
  - 当前还没有 README 和本地验收脚本说明
- 下一步：
  - 进入模块 05 任务 05：补调用生命周期控制与失败处理

#### 记录 034：完成模块 05 任务 03，实现最小 provider 适配器

- 状态：已完成
- 范围：完成模块 05 中“任务 03：实现最小 provider 适配器”
- 结果：
  - 已新增 `src/mindwiki/llm/providers/openai_compatible.py`
  - 已建立第一版 `OpenAI-compatible /chat/completions` 适配器：
    - `OpenAICompatibleConfig`
    - `OpenAICompatibleProvider`
  - 当前 provider 已支持的最小能力包括：
    - 将统一 `LLMRequest` 转换为 `/chat/completions` 请求 payload
    - 组装 `Authorization: Bearer <api_key>` 请求头
    - 以 `POST {base_url}/chat/completions` 发起调用
    - 将 provider 返回解析为统一 `LLMResponse`
    - 承接 `output_text`
    - 承接 `provider_response_id`
    - 承接 `finish_reason`
    - 承接 `usage`
    - 对缺失 `choice` 或空 `message.content` 的返回标记 `protocol_validation_failed`
    - 对 `HTTPError` 和 `URLError` 做最小错误归一化
  - 当前错误映射策略已落地：
    - `429` 和 `5xx` 归为可重试 `http_error`
    - 其他 HTTP 错误归为不可重试 `http_error`
    - 网络错误归为可重试 `network_error`
  - 本轮实现仍保持边界收敛：
    - 尚未引入 service 层统一重试循环
    - 尚未发起真实业务级 `generate_text` 调用
    - 尚未接入结构化 schema 校验与 repair
  - 已新增 `tests/test_llm_provider.py`，覆盖：
    - payload 组装
    - 成功响应解析
    - `missing_choice` 协议失败
    - `HTTP 429` 错误映射
    - 网络错误映射
- 验证结果：
  - `python3 -m pytest tests/test_llm_models.py tests/test_llm_provider.py tests/test_cli.py` 通过
  - 当前共 `33` 个测试，全部通过
- 遗留问题：
  - 当前 provider 还没有从 service 层统一装配
  - 当前尚未使用真实 `.env` 配置发起一次端到端模型调用
  - README 还未说明 LLM 本地联调方式
- 下一步：
  - 进入模块 05 任务 04：实现 `generate_text` 最小可用链路

#### 记录 033：完成模块 05 任务 02，建立统一 `LLMRequest / LLMResponse` 协议

- 状态：已完成
- 范围：完成模块 05 中“任务 02：建立统一 `LLMRequest / LLMResponse` 协议”
- 结果：
  - 已新增 `src/mindwiki/llm/models.py`，建立第一版统一协议模型：
    - `LLMMessage`
    - `RetryPolicy`
    - `ValidationIssue`
    - `ValidationResult`
    - `LLMValidation`
    - `ResponseTiming`
    - `LLMError`
    - `LLMRequest`
    - `LLMResponse`
  - `LLMRequest` 当前已承接第一版最小请求字段：
    - `task_type`
    - `model`
    - `messages`
    - `temperature`
    - `top_p`
    - `max_tokens`
    - `response_format`
    - `stream`
    - `timeout_ms`
    - `retry_policy`
    - `metadata`
  - `LLMResponse` 当前已承接第一版最小返回字段：
    - `request_id`
    - `model`
    - `output_text`
    - `status`
    - `parsed_output`
    - `validation`
    - `timing`
    - `error`
    - `provider_response_id`
    - `finish_reason`
    - `usage`
    - `raw_response`
  - 已扩展 `src/mindwiki/infrastructure/settings.py`，增加 LLM 相关配置读取：
    - `LLM_BASE_URL`
    - `LLM_API_KEY`
    - `LLM_MODEL_ID`
    - `LLM_MODEL_MINI_ID`
    - `LLM_TIMEOUT_MS`
  - 已更新 `.env.example`，补充 LLM 配置占位示例，但未写入真实密钥
  - 已新增 `tests/test_llm_models.py`，覆盖：
    - `LLMRequest` 字段结构
    - `LLMResponse` 校验与错误字段
    - `.env` 中 LLM 配置读取行为
- 验证结果：
  - `python3 -m pytest tests/test_llm_models.py tests/test_cli.py` 通过
  - 当前共 `27` 个测试，全部通过
- 遗留问题：
  - 当前还没有 provider 实现，协议尚未真正发起 HTTP 调用
  - 当前还没有 `generate_text` 服务入口
  - `citation_validation` 目前只是协议占位，尚未接入真实证据集校验
- 下一步：
  - 进入模块 05 任务 03：实现最小 provider 适配器

#### 记录 032：完成模块 05 任务 01，LLM 设计对接与当前代码差异修正

- 状态：已完成
- 范围：完成模块 05 中“任务 01：LLM 设计对接与当前代码差异修正”
- 结果：
  - 已对照 `Step 15.1 ~ 15.7` 与当前代码结构完成第一轮对接
  - 已确认当前工程现状：
    - 目前只有导入链路与 PostgreSQL 持久化能力
    - CLI 仅包含 `import file` / `import dir`
    - `src/mindwiki/infrastructure/settings.py` 当前只承接 `MINDWIKI_DATABASE_URL`
    - 当前没有任何模型请求协议、provider 适配器、模型服务入口、输出校验或调用观测实现
  - 已确认模块 05 第一版应收敛为“模型服务层基础能力”，而不是直接实现完整 RAG 问答
  - 已确认第一版优先落地范围：
    - 建立统一 `LLMRequest / LLMResponse` 基础模型
    - 建立最小 provider 抽象与一个 `OpenAI-compatible /chat/completions` 适配器
    - 建立 `generate_text` 单一能力入口，先证明真实模型调用链路可跑通
    - 建立最小调用控制字段承接：
      - `request_id`
      - `attempt_id`
      - `timeout_ms`
      - `max_retries`
      - `allow_fallback`
    - 建立最小返回承接：
      - `parsed_output`
      - `validation`
      - `timing`
      - `status`
      - `error`
  - 已确认第一版暂不进入的范围：
    - `generate_subqueries`
    - `generate_step_back_query`
    - `generate_hyde_query`
    - `rerank_with_llm`
    - 多 provider 智能路由
    - 复杂 quota / 并发控制
    - 重型 tracing / 持久化调用日志平台
    - 与检索编排层、最终问答层的完整集成
  - 已确认建议的最小工程落点：
    - `src/mindwiki/llm/models.py`
      - 放 `LLMRequest`、`LLMResponse`、重试策略、校验结果等基础模型
    - `src/mindwiki/llm/service.py`
      - 放统一 `generate_text` 入口与最小调用生命周期控制
    - `src/mindwiki/llm/providers/`
      - 放 provider 协议与 `OpenAI-compatible` 适配器
    - `src/mindwiki/infrastructure/settings.py`
      - 扩展 LLM 相关配置读取
    - `tests/`
      - 先补协议、provider 适配与 `generate_text` 的最小单测
- 当前识别的关键配置缺口：
  - `.env.example` 目前只有数据库配置
  - 第一版至少需要新增：
    - `LLM_BASE_URL`
    - `LLM_API_KEY`
    - `LLM_MODEL_ID`
    - 可选的 `LLM_TIMEOUT_MS`
- 设计对接结论：
  - `15.2` 统一调用协议可以先收敛为最小 `system + user` 消息结构
  - `15.4` 生命周期控制第一版先实现超时、有限重试和标准错误分类承接，不先做复杂 fallback 链
  - `15.5` 结构化输出校验第一版先承接 `protocol_validation` 与 `schema_validation`，`citation_validation` 留待后续真正接入检索证据集后再落
  - `15.6` 成本、配额、并发控制第一版先保留字段与配置入口，不在当前任务中做重实现
  - `15.7` 调用观测第一版先保留内存级/返回级摘要字段，不立即新增数据库日志表
- 遗留问题：
  - 当前还未确定第一版实际对接的 provider 与模型名称
  - 当前还未引入任何 HTTP 客户端依赖
  - 当前 README 尚未说明 LLM 本地配置与最小验证方式
- 下一步：
  - 进入模块 05 任务 02：建立统一 `LLMRequest / LLMResponse` 协议

#### 记录 031：将模块 05 调整为 LLM 接入基础模块 MVP

- 状态：进行中
- 范围：根据新完成的 Step 15 LLM 设计稿，调整第五个开发模块的目标与任务拆解，不再继续沿用“检索前置能力对齐 MVP”的模块定义
- 结果：
  - 已确认当前代码仍未接入任何真实 LLM 调用能力：
    - 尚无统一模型调用协议
    - 尚无 provider 适配器
    - 尚无 `generate_text` 最小生成链路
    - 尚无超时、重试、fallback、结构化输出校验等模型服务控制能力
  - 已确认 `doc/design/step-15-llm-module-and-model-service/` 相关设计稿已完成，当前更适合作为下一开发模块的直接承接目标
  - 已将模块 05 的目标从“检索前置能力对齐”调整为“LLM 接入基础模块 MVP”
  - 已将模块 05 的任务拆解调整为：
    - 任务 01：LLM 设计对接与当前代码差异修正
    - 任务 02：建立统一 `LLMRequest / LLMResponse` 协议
    - 任务 03：实现最小 provider 适配器
    - 任务 04：实现 `generate_text` 最小可用链路
    - 任务 05：补调用生命周期控制与失败处理
    - 任务 06：补结构化输出校验与返回约定
    - 任务 07：补 README、本地配置说明与验收脚本
- 调整原因：
  - 当前系统虽然已完成导入与基础落库，但仍没有任何真实 LLM 接入能力
  - Step 15 已提供独立的模型服务层设计，适合作为下一模块先行落地
  - 若继续推进检索前置能力而不建立模型调用底座，后续 Step 09 / Step 10 / Step 15 的许多能力都缺少真实承接入口
- 遗留问题：
  - 原模块 05 中“标签落库、定位信息、最小检索投影”等内容仍有价值，但不再作为当前优先模块
  - 这些内容后续可回收到检索实现相关模块中继续处理
- 下一步：
  - 开始模块 05 任务 01：LLM 设计对接与当前代码差异修正

#### 记录 030：完成模块 05 任务 01，检索前置能力对接与差异修正

- 状态：已完成
- 范围：完成模块 05 中“任务 01：检索设计对接与差异修正”
- 结果：
  - 已对照 Step 08 / Step 09 设计与当前代码、数据库结构完成第一轮对接
  - 已确认当前实现与设计一致的部分：
    - 第一阶段检索主对象统一为 `chunk`
    - PDF 已具备最小 `page_number` 定位承接
    - `document_title / section_title / chunk_text / source_type` 已具备最小数据基础
    - 后续可围绕统一 `chunk hit` 返回结构继续实现
  - 已确认当前实现与设计存在的主要差异：
    - `document_tags` 尚未真实落库，因此模块 05 当前阶段不能把标签查询作为已实现能力
    - Markdown 尚未真实落库 `line_start / line_end`，因此 citation `location` 只能先提供最小版本
    - 当前尚无 embedding、vector index、hybrid fusion，因此 `retrieval_mode` 暂不能完整实现设计中的 `hybrid / vector_only / bm25_only`
    - 当前尚无 `match_sources / score_breakdown / snippet` 的真实返回承接
    - Step 09 的 `sub-query / rerank / context builder` 依赖检索基础层先落稳，本模块不直接跨入完整编排实现
  - 基于上述差异，已将模块 05 当前阶段的目标修正为：
    - 先补齐检索前置能力，而不是直接进入检索实现
    - 先修正 Step 08 / Step 09 依赖的关键数据承接差异
    - 先为后续 BM25、vector、hybrid、citation payload 提供稳定基础
    - 不直接进入 Step 09 的编排层完整实现
  - 当前阶段正式收敛后的实现边界为：
    - 优先补：
      - 标签真实落库
      - 最小定位信息持久化
      - 统一检索结果所需的最小数据投影
    - 暂不承诺：
      - `bm25_only` 检索路径
      - `vector_only` 检索路径
      - `hybrid` 检索路径
      - rerank
      - context builder
    - citation `location` 当前目标调整为先补最小承接字段，而不是立即完成完整返回协议
- 遗留问题：
  - 若后续希望完整对齐 `8.4` 中的 `document_tags` 命中能力，需要先补标签真实落库
  - 若后续希望完整对齐 `9.6` 的 Markdown 跳转能力，需要先补 `line_start / line_end` 的真实持久化
  - 检索真正实现前，仍需先补最小数据投影与前置验证能力
- 下一步：
  - 进入模块 05 任务 02：补标签真实落库与文档级标签承接

#### 记录 029：确定模块 05 为检索前置能力对齐 MVP

- 状态：进行中
- 范围：将第五个开发模块正式定义为“检索前置能力对齐 MVP”，在 Step 08 和 Step 09 设计已完成、模块 04 已完成导入与入库闭环的基础上，先补齐检索真正落地前所需的关键数据基础与设计对接
- 结果：
  - 明确模块 05 不直接进入 embedding、vector retrieval、hybrid fusion、rerank 和 context builder 的完整实现
  - 明确模块 05 的目标是“先完成检索设计与当前实现的对接修正，再补齐检索前置能力”
  - 明确模块 05 当前阶段只先实现：
    - 标签真实落库与文档级标签承接
    - 最小定位信息持久化
    - 统一检索结果所需的最小数据投影
    - 检索前置能力的本地验收脚本
  - 明确模块 05 的任务 01 主要用于“对接工作”，需要显式对照 Step 08 / Step 09 和当前代码状态，修正设计目标与落地现状之间的出入
- 当前已识别的设计与实现差异：
  - Step 08 设计中包含 `tags / source_types / time_range / document_scope` 强过滤，但当前代码里 `tags` 尚未真实落库到 `tags/document_tags`
  - Step 09 / `9.6` 的 citation `location` 已有设计，但当前实现仅具备较粗粒度定位：
    - Markdown 尚未真实落库 `line_start / line_end`
    - PDF 当前只有 `chunks.page_number`
  - Step 08 设计中 `retrieval_mode` 支持 `hybrid / vector_only / bm25_only`，但当前尚无 embedding、vector index 和 hybrid fusion 能力
  - Step 08 设计中的 `match_sources / score_breakdown / snippet` 返回结构尚无真实实现承接
  - Step 09 的 sub-query / rerank / context builder 依赖检索基础层先稳定落地，因此模块 05 不应直接跨到编排层完整实现
- 模块目标：
  - 完成 Step 08 / Step 09 与当前实现的差异对接
  - 补齐标签、定位信息和最小结果投影等检索前置能力
  - 为后续 BM25、vector、hybrid 和 citation payload 提供稳定数据基础
  - 提供检索前置能力的本地验收脚本和 README 说明
- 分步任务拆解：
  - 任务 01：检索设计对接与差异修正
  - 任务 02：补标签真实落库与文档级标签承接
  - 任务 03：补最小定位信息持久化
  - 任务 04：补统一检索结果所需的最小数据投影
  - 任务 05：补检索前置能力的本地验收脚本与 README 说明
- 当前建议执行顺序：
  - 先完成设计与当前实现的差异对接
  - 再补标签与定位信息
  - 然后补最小结果投影
  - 最后补本地验收
- 遗留问题：
  - 当前检索相关设计虽然已完成 Step 08 / Step 09，但仍需先与现有入库结构逐项对齐
  - 当前代码尚未建立任何正式检索层实现
- 下一步：
  - 开始模块 05 任务 01：检索设计对接与差异修正

### 2026-04-26

#### 记录 028：完成模块 04 任务 04-05，打通目录 PDF 执行并升级本地验收链路

- 状态：已完成
- 范围：完成模块 04 中以下任务：
  - 任务 04：让目录导入执行阶段真正消费 PDF 子任务
  - 任务 05：补 PDF 本地验收脚本与 README 说明
- 结果：
  - 目录导入执行阶段中的 PDF 子任务，已不再使用 `pdf_parsing_not_implemented` 的执行期跳过逻辑
  - 当前目录中的可复制文本 PDF 子任务会复用单文件 PDF 导入主链路，执行真实状态流转：
    - `pending -> running -> success`
    - 提取失败时回写为 `failed`
  - 当前目录执行统计中，PDF 子任务结果会真实计入：
    - `success_jobs`
    - `failed_jobs`
  - `scripts/verify_local_directory_import.py` 已升级为真实生成可提取文本 PDF，并按新口径校验目录导入结果
  - `README.md` 与 `scripts/README.md` 已同步更新目录 PDF 执行行为说明
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 24 个测试
  - `python3 -m py_compile scripts/verify_local_directory_import.py` 通过
  - 真实执行 `PYTHONPATH=src /opt/miniconda3/bin/python3 scripts/verify_local_directory_import.py` 成功，退出码为 `0`
  - 本次真实目录导入返回：
    - `batch_job_id = f45190b0-7f03-4cc1-a948-3273b869b132`
    - `success_jobs = 1`
    - `failed_jobs = 0`
    - `executed_skipped_jobs = 0`
    - `pending_jobs = 1`
    - `skipped_jobs = 3`
  - 针对该批次父任务的数据库回查结果为：
    - `input_payload.execution_summary.success_jobs = 1`
    - `input_payload.execution_summary.failed_jobs = 0`
    - `input_payload.execution_summary.executed_skipped_jobs = 0`
  - 针对该批次子任务的数据库回查结果为：
    - `a.md -> skipped / content_unchanged`
    - `b.pdf -> success`
    - `c.txt -> skipped / unsupported_file_type`
    - `d.md -> skipped / empty_file`
  - 本次真实验收的总增量为：
    - `sources +2`
    - `import_jobs +6`
    - `documents +2`
    - `sections +3`
    - `chunks +3`
- 遗留问题：
  - 当前目录 PDF 执行仍只覆盖可复制文本 PDF
  - 当前未纳入 OCR
- 下一步：
  - 模块 04 的 5 个任务已全部完成
  - 下一阶段可开始讨论模块 05 的目标与任务拆分

#### 记录 027：完成模块 04 任务 03，将 PDF 接入统一导入落库链路

- 状态：已完成
- 范围：完成模块 04 中“任务 03：将 PDF 接入统一导入落库链路”
- 结果：
  - `mindwiki import file <pdf>` 在有数据库配置时，已接入真实 `import_job` 状态流转：
    - `pending -> running -> success/failed`
  - PDF 已复用现有 `sources / import_jobs / documents / sections / chunks` 表结构落库
  - 当前落库约定为：
    - `sources.source_type = pdf`
    - `documents.document_type = pdf`
    - 每页一个 `section`
    - 每页正文一个 `chunk`
    - `chunks.page_number` 写入对应页码
  - 当前无码库环境下，PDF 单文件导入会与 Markdown 保持一致，返回：
    - `persistence=skipped`
    - `reason=database_url_missing`
  - 当前 PDF 单文件导入失败时，会按真实执行失败回写 `failed`
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 23 个测试
  - `python3 -m py_compile src/mindwiki/infrastructure/import_repository.py src/mindwiki/application/import_service.py tests/test_cli.py` 通过
  - 真实执行 PDF 单文件导入成功，返回：
    - `import_job_id = c3dffe34-cc2b-4743-bd9c-b857ae09c07c`
    - `document_id = bff44d2b-0373-418d-a31b-256dfb4b1f10`
    - `chunks = 1`
  - 针对该次 PDF 导入的数据库回查结果为：
    - `documents.document_type = pdf`
    - `chunks.page_number = 1`
    - `chunk_rows = 1`
- 遗留问题：
  - 当前目录导入执行阶段仍未真正消费 PDF 子任务
  - 当前仅覆盖可复制文本 PDF，未纳入 OCR
- 下一步：
  - 进入模块 04 任务 04：让目录导入执行阶段真正消费 PDF 子任务

#### 记录 026：完成模块 04 任务 02，实现 PDF 单文件读取与文本提取

- 状态：已完成
- 范围：完成模块 04 中“任务 02：实现 PDF 单文件读取与文本提取”
- 结果：
  - 新增 `src/mindwiki/ingestion/pdf.py`
  - 当前已接入基于 `pypdf` 的最小 PDF 文本提取能力
  - 当前 PDF 解析输出已对齐统一导入中间结构，包含：
    - `title`
    - `raw_text`
    - `sections`
    - `page_count`
  - 当前采用“按页切 section”的最小策略：
    - 每页生成一个 section
    - `section.title = Page N`
    - `section.content` 保存该页提取文本
  - 当前无稳定标题时，`title` 回退为文件名
  - `mindwiki import file <pdf>` 已不再返回旧的 `parsing=pending`
  - 当前 PDF 单文件导入会返回：
    - `pages=...`
    - `sections=...`
    - `parsing=completed`
    - `reason=pdf_persistence_not_implemented`
  - 当前失败语义已区分为：
    - `pdf_read_failed`
    - `pdf_text_extraction_failed`
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 21 个测试
  - `python3 -m py_compile src/mindwiki/ingestion/pdf.py src/mindwiki/application/import_service.py tests/test_cli.py` 通过
  - 真实执行 PDF 单文件导入成功，返回：
    - `type = .pdf`
    - `title = sample`
    - `pages = 1`
    - `sections = 1`
    - `parsing = completed`
    - `reason = pdf_persistence_not_implemented`
- 遗留问题：
  - 当前 PDF 仍未接入 PostgreSQL 落库
  - 当前目录导入执行阶段仍未真正消费 PDF 子任务
  - 当前仅覆盖可复制文本 PDF，未纳入 OCR
- 下一步：
  - 进入模块 04 任务 03：将 PDF 接入统一导入落库链路

#### 记录 025：完成模块 04 任务 01，明确 PDF 第一阶段解析策略

- 状态：已完成
- 范围：完成模块 04 中“任务 01：明确 PDF 第一阶段解析策略”
- 结果：
  - 明确第一阶段只支持“可复制文本 PDF”
  - 判断标准不只看文件扩展名，而是实际能否提取出有效正文文本
  - 当前阶段不纳入：
    - OCR
    - 图片型扫描 PDF
    - 表格结构恢复
    - 多栏版面重排优化
    - 页眉页脚智能清洗
  - 明确 PDF 第一阶段的最小解析结果将对齐现有统一导入中间结构：
    - `title`
    - `raw_text`
    - `sections`
    - 每个 `section.content`
  - 明确当前阶段无稳定标题时，`title` 回退为文件名
  - 明确当前阶段采用“按页切 section”的最小策略：
    - 每页一个 section
    - `section.title` 可为空，或使用 `Page N`
    - `section.content` 保存该页文本
  - 明确 PDF 执行失败语义：
    - 可打开但无法提取有效文本，按 `failed` 处理
    - 当前 OCR 未实现导致无法处理扫描版 PDF，按 `failed` 处理
  - 明确当前阶段不再把已进入执行链路的 PDF 失败记为 `skipped`
- 遗留问题：
  - 具体采用哪一个 PDF 文本提取库，仍需在任务 02 实现时结合本地环境确认
  - 现有 `sections/chunks` 结构中的页码承接方式，还需要在实现中进一步收敛
- 下一步：
  - 进入模块 04 任务 02：实现 PDF 单文件读取与文本提取

#### 记录 024：确定模块 04 为 PDF 导入与解析 MVP

- 状态：进行中
- 范围：将第四个开发模块正式定义为“PDF 导入与解析 MVP”，在模块 03 已完成目录执行闭环的基础上，补齐 PDF 从 CLI 接收到真实落库的最小链路
- 结果：
  - 明确模块 04 不进入 OCR，也不直接跳到检索，而是先打通可复制文本 PDF 的最小导入能力
  - 明确模块 04 的目标是“能执行 PDF 单文件导入、能让目录导入真实消费 PDF 子任务、能形成最小可落库结构、能保留最小定位信息、能提供本地验收链路”
  - 明确当前阶段的 PDF 处理边界为：
    - 只处理可复制文本 PDF
    - 不处理 OCR
    - 扫描版或图片版 PDF 当前允许失败或跳过，但需要给出明确原因
  - 明确当前阶段的 PDF 结构策略为：
    - 优先保证可入库、可追踪、可后续检索
    - 第一版允许采用按页或连续正文的最小切分策略
    - 没有稳定标题结构时，允许生成无标题 section
- 模块目标：
  - `mindwiki import file <pdf>` 能真正执行
  - 目录导入执行阶段能真实消费 PDF 子任务
  - PDF 能写入最小 `document / section / chunk` 结构
  - 保留最小定位信息，为后续引用和检索做准备
  - 提供 PDF 本地验收脚本和 README 说明
- 分步任务拆解：
  - 任务 01：明确 PDF 第一阶段解析策略
  - 任务 02：实现 PDF 单文件读取与文本提取
  - 任务 03：将 PDF 接入统一导入落库链路
  - 任务 04：让目录导入执行阶段真正消费 PDF 子任务
  - 任务 05：补 PDF 本地验收脚本与 README 说明
- 当前建议执行顺序：
  - 先确定 PDF 第一阶段解析边界
  - 再补单文件读取与文本提取
  - 然后接入统一落库链路
  - 最后补目录执行和本地验收
- 遗留问题：
  - 当前代码路径里 `.pdf` 仍未进入真实解析链路
  - PDF 页级定位字段如何在现有 `sections/chunks` 结构中最小承接，还需要实现时进一步收敛
  - OCR 是否独立成后续模块，当前已暂定不纳入模块 04
- 下一步：
  - 开始模块 04 任务 01：明确 PDF 第一阶段解析策略

#### 记录 023：完成模块 03 任务 04-05，补齐目录执行后汇总与验收链路

- 状态：已完成
- 范围：完成模块 03 中以下任务：
  - 任务 04：补目录总任务执行后统计与状态汇总
  - 任务 05：补目录执行链路的本地验收脚本和 README 说明
- 结果：
  - 目录导入 CLI 输出现在已明确区分两层统计口径：
    - 建任务阶段统计：`pending_jobs`、`skipped_jobs`、`skipped_unsupported`、`skipped_empty`、`skipped_unchanged`
    - 执行阶段统计：`success_jobs`、`failed_jobs`、`executed_skipped_jobs`
  - 父批次任务当前仍保持 `status = success`
  - 父批次任务的 `input_payload` 已补充：
    - `execution_summary.success_jobs`
    - `execution_summary.failed_jobs`
    - `execution_summary.executed_skipped_jobs`
  - `scripts/verify_local_directory_import.py` 已升级到目录执行链路新口径
  - `README.md` 与 `scripts/README.md` 已补充父任务执行汇总和目录验收脚本说明
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 17 个测试
  - `python3 -m py_compile scripts/verify_local_directory_import.py` 通过
  - 真实执行 `PYTHONPATH=src /opt/miniconda3/bin/python3 scripts/verify_local_directory_import.py` 成功，退出码为 `0`
  - 本次真实目录导入返回：
    - `batch_job_id = 627e9165-05d9-47fd-97de-f9c5acc03752`
    - `success_jobs = 0`
    - `failed_jobs = 0`
    - `executed_skipped_jobs = 1`
    - `pending_jobs = 1`
    - `skipped_jobs = 3`
  - 针对该批次父任务的数据库回查结果为：
    - `input_payload.execution_summary.success_jobs = 0`
    - `input_payload.execution_summary.failed_jobs = 0`
    - `input_payload.execution_summary.executed_skipped_jobs = 1`
  - 针对该批次子任务的数据库回查结果为：
    - `a.md -> skipped / content_unchanged`
    - `b.pdf -> skipped / pdf_parsing_not_implemented`
    - `c.txt -> skipped / unsupported_file_type`
    - `d.md -> skipped / empty_file`
- 遗留问题：
  - 当前父任务状态模型仍保持最小实现，尚未引入 `partial_success`
  - 目录执行链路目前仍未覆盖 PDF 真实解析与真实成功写入
- 下一步：
  - 模块 03 的 5 个任务已全部完成
  - 下一阶段可开始讨论模块 04 的目标与任务拆分

#### 记录 022：完成模块 03 任务 01-03，打通目录导入执行入口

- 状态：已完成
- 范围：完成模块 03 中以下任务的最小闭环实现：
  - 任务 01：批量消费目录导入中的 `pending` 子任务
  - 任务 02：复用单文件 Markdown 导入链路，完成批量真实落库
  - 任务 03：为暂未实现解析的 PDF 明确执行策略
- 结果：
  - 目录导入在创建子任务后，已不再停留在“只建任务”阶段
  - 当前会在同一次 `mindwiki import dir <path>` 命令中继续消费新创建的 `pending` 子任务
  - 本次主完成项是“任务 01：打通目录子任务消费入口”
  - 同时一并落地了：
    - 任务 02 的最小实现：Markdown 子任务复用现有单文件导入主链路完成真实落库
    - 任务 03 的最小实现：PDF 子任务在当前执行阶段标记为 `skipped / pdf_parsing_not_implemented`
  - 为避免重复建任务，目录子任务执行时会直接复用已存在的子任务 `import_job_id`
  - Markdown 子任务已复用现有单文件 Markdown 导入主链路，并将子任务状态更新为：
    - `pending -> running -> success`
    - 失败时回写为 `failed`
  - PDF 子任务当前会在执行阶段被更新为：
    - `pending -> skipped`
    - `error_message = pdf_parsing_not_implemented`
  - 当前目录导入输出已补充最小执行结果字段：
    - `success_jobs`
    - `failed_jobs`
    - `executed_skipped_jobs`
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 17 个测试
  - 新增覆盖：
    - 目录导入执行 Markdown 子任务且复用既有子任务 ID
    - 目录导入执行阶段跳过 PDF 子任务
    - 目录导入执行阶段 Markdown 解析失败时回写子任务 `failed`
- 遗留问题：
  - 当前 `pending_jobs` 等字段仍表示“建任务阶段”的统计，执行后汇总口径还需在后续任务继续收敛
  - 当前环境下通过沙箱直接做真实 PostgreSQL 目录执行验收会受到本地连接限制影响，本次以单元测试作为主要验收依据
- 下一步：
  - 继续模块 03 任务 04：补目录总任务执行后统计与状态汇总

#### 记录 021：确定模块 03 为目录导入执行闭环 MVP

- 状态：进行中
- 范围：将第三个开发模块正式定义为“目录导入执行闭环 MVP”，在模块 02 已完成的目录扫描、子任务创建和增量跳过基础上，补齐真正的批量执行能力
- 结果：
  - 明确模块 03 不直接进入检索或前端，而是先补齐目录导入执行闭环
  - 明确模块 03 的目标是“能消费 `pending` 子任务、能真实执行 Markdown 批量导入、能明确 PDF 当前执行策略、能汇总父任务执行结果”
  - 明确当前阶段的执行策略为：
    - `.md` 子任务真实执行并落库
    - `.pdf` 子任务暂标记为 `skipped`，原因使用 `pdf_parsing_not_implemented`
    - 父批次任务在执行链路跑完后先统一记为 `success`
    - 实际执行结果通过统计字段体现，而不在当前阶段引入 `partial_success`
- 模块目标：
  - 目录导入可真正消费 `pending` 子任务
  - 支持批量复用现有单文件 Markdown 导入链路
  - 明确 PDF 在批量执行阶段的最小处理策略
  - 输出目录执行后的成功/失败/跳过统计
  - 形成父任务和子任务的最小执行闭环
- 分步任务拆解：
  - 任务 01：批量消费目录导入中的 `pending` 子任务
  - 任务 02：复用单文件 Markdown 导入链路，完成批量真实落库
  - 任务 03：为暂未实现解析的 PDF 明确执行策略
  - 任务 04：补目录总任务执行后统计与状态汇总
  - 任务 05：补目录执行链路的本地验收脚本和 README 说明
- 当前建议执行顺序：
  - 先补子任务消费入口
  - 再接 Markdown 批量真实执行
  - 然后收敛 PDF 当前处理策略
  - 最后补统计汇总和本地验收
- 遗留问题：
  - 当前目录导入仍然只停留在“扫描与建任务”阶段
  - PDF 真实解析链路尚未实现
  - 父任务状态模型后续是否需要引入 `partial_success` 仍待未来阶段再判断
- 下一步：
  - 开始模块 03 任务 01：批量消费目录导入中的 `pending` 子任务

#### 记录 020：完成模块 02 任务 07 目录导入本地验收脚本

- 状态：已完成
- 范围：完成模块 02 中“任务 07：补充目录导入本地验收脚本”
- 结果：
  - 新增 `scripts/verify_local_directory_import.py`
  - 新脚本会创建临时目录，并同时构造：
    - 已支持的 Markdown 文件
    - 已支持但未解析的 PDF 文件
    - 不支持文件
    - 空 Markdown 文件
  - 脚本会先执行一次单文件 Markdown 导入，制造“同路径同内容”的增量基线
  - 随后执行 `mindwiki import dir ...`
  - 脚本会校验：
    - 目录导入 CLI 统计摘要字段
    - `batch_job_id` 对应的子任务状态和错误原因
    - `sources`、`import_jobs`、`documents`、`sections`、`chunks` 的增量变化
  - `README.md` 与 `scripts/README.md` 已补充脚本说明
- 验证结果：
  - `python3 -m py_compile scripts/verify_local_directory_import.py` 通过
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 16 个测试
  - 真实执行 `PYTHONPATH=src /opt/miniconda3/bin/python3 scripts/verify_local_directory_import.py` 成功，退出码为 `0`
  - 本次真实目录导入返回：
    - `batch_job_id = f2ae7a74-76a7-43d1-a60d-292f1b07d995`
    - `pending_jobs = 1`
    - `skipped_jobs = 3`
    - `skipped_unsupported = 1`
    - `skipped_empty = 1`
    - `skipped_unchanged = 1`
  - 针对该批次的数据库回查结果为：
    - `a.md -> skipped / content_unchanged`
    - `b.pdf -> pending`
    - `c.txt -> skipped / unsupported_file_type`
    - `d.md -> skipped / empty_file`
  - 本次真实验收的总增量为：
    - `sources +1`
    - `import_jobs +6`
    - `documents +1`
    - `sections +2`
    - `chunks +2`
- 遗留问题：
  - 脚本当前仍沿用现有 CLI 文本输出解析方式，对含空格字段的 `parsed_output` 仍是近似摘要，但不影响本次目录导入验收判断
  - 验收脚本当前只覆盖“目录扫描与子任务创建”阶段，尚未覆盖后续真正的批量消费执行
- 下一步：
  - 模块 02 的 7 个任务已全部完成
  - 下一阶段可开始整理模块 03 的目标与任务拆分

#### 记录 019：完成模块 02 任务 06 目录导入统计摘要输出

- 状态：已完成
- 范围：完成模块 02 中“任务 06：实现目录导入统计摘要输出”
- 结果：
  - 目录导入 CLI 输出已补充任务级统计摘要
  - 当前新增统计字段包括：
    - `pending_jobs`
    - `skipped_jobs`
    - `skipped_unsupported`
    - `skipped_empty`
    - `skipped_unchanged`
  - 统计来源已从仓储层结构化返回，而不是在 CLI 层二次推断
  - 当未配置数据库时，CLI 仍会基于扫描结果输出最小统计摘要，其中 `skipped_unchanged = 0`
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 16 个测试
  - 真实目录导入示例返回：
    - `batch_job_id = fadde13b-31d6-477e-86e6-dcd27c006756`
    - `pending_jobs = 1`
    - `skipped_jobs = 1`
    - `skipped_unchanged = 1`
  - 同次真实单文件导入已先成功写入本地库，用于制造“同路径同内容”的增量跳过场景
- 遗留问题：
  - 当前统计仍停留在“目录扫描与子任务创建”阶段，尚未覆盖真实批量执行后的成功/失败汇总
  - 真实数据库子任务明细回查受本地权限审批链路波动影响，本次以真实 CLI 输出和单元测试作为主要验收依据
- 下一步：
  - 进入模块 02 任务 07：补充目录导入本地验收脚本

#### 记录 018：完成模块 02 任务 05 基于 `content_hash` 的最小增量跳过

- 状态：已完成
- 范围：完成模块 02 中“任务 05：实现基于 `content_hash` 的最小增量跳过”
- 结果：
  - 目录导入创建支持文件子任务时，已接入最小增量判断
  - 当前判断规则为：
    - 同一路径且 `content_hash` 相同：创建 `skipped` 子任务，`error_message = content_unchanged`
    - 同一路径但内容变化：仍创建为 `pending`
    - 不同路径即使内容相同：仍按新文件处理
  - 子任务 payload 已补充 `content_hash` 和 `skip_reason`
  - 该任务边界仍保持在“创建目录子任务时做最小增量跳过”，尚未进入真正的批量消费执行
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 16 个测试
  - 使用真实 PostgreSQL 再次执行目录导入，返回：
    - `batch_job_id = ce232dae-5af5-4aeb-b90e-e0a51aabeb10`
    - `child_jobs = 2`
  - 针对该批次的数据库回查结果为：
    - `a.md -> skipped / content_unchanged`
    - `b.pdf -> pending`
- 遗留问题：
  - 当前增量判断仅覆盖“同路径 + 同内容”的最小场景
  - 目录导入仍未真正消费这些 `pending` 子任务
  - 目录导入 CLI 还未输出更细粒度的统计摘要
- 下一步：
  - 进入模块 02 任务 06：实现目录导入统计摘要输出

#### 记录 017：完成模块 02 任务 04 不支持文件和空文件的 `skipped` 记录

- 状态：已完成
- 范围：完成模块 02 中“任务 04：实现不支持文件和空文件的 `skipped` 记录”
- 结果：
  - 目录扫描结果已增加 `empty_files` 分类
  - 目录导入返回结果已增加：
    - `empty_files=...`
    - `empty_names=...`
  - 目录导入落库时：
    - 支持文件仍创建为 `pending` 子任务
    - 不支持文件创建为 `skipped` 子任务，`error_message = unsupported_file_type`
    - 空文件创建为 `skipped` 子任务，`error_message = empty_file`
  - 目录总任务 payload 已补充支持文件数、不支持文件数和空文件数
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 15 个测试
  - 真实目录导入示例返回：
    - `supported_files=2`
    - `unsupported_files=1`
    - `empty_files=1`
    - `child_jobs=4`
  - 针对最新 `batch_job_id = b1b57a20-c058-4754-9035-cf7b850b140c` 的数据库回查结果为：
    - `pending = 2`
    - `skipped / unsupported_file_type = 1`
    - `skipped / empty_file = 1`
- 遗留问题：
  - 当前 `skipped` 仅覆盖不支持文件和空文件，增量跳过仍待后续任务实现
  - 目录导入尚未真正消费这些 `pending` 子任务
  - 目录总任务状态汇总仍未覆盖更细粒度统计
- 下一步：
  - 进入模块 02 任务 05：实现基于 `content_hash` 的最小增量跳过

### 2026-04-26

#### 记录 016：完成模块 02 任务 03 目录导入总任务与文件子任务落库

- 状态：已完成
- 范围：完成模块 02 中“任务 03：实现目录导入总任务与文件子任务落库”
- 结果：
  - 目录导入在有数据库配置时，已支持创建一个 `dir` 类型总任务
  - 当前会为扫描出的每个支持文件创建一个 `file` 类型子任务
  - 子任务通过 `parent_job_id` 关联到总任务
  - 当前总任务状态采用 `success`，子任务状态采用 `pending`，用于表示“批量导入任务结构已创建，文件任务待后续处理”
  - 目录导入 CLI 返回结果已补充：
    - `job_persistence=stored`
    - `batch_job_id=...`
    - `child_jobs=...`
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 15 个测试
  - 真实目录导入示例验证成功，返回了真实 `batch_job_id`
  - 真实目录导入示例中，2 个支持文件生成了 `child_jobs=2`
- 遗留问题：
  - 当前仅为支持文件创建子任务，不支持文件和空文件的 `skipped` 记录仍待后续补齐
  - 当前目录导入尚未真正批量执行这些子任务
  - 总任务状态汇总还未覆盖“部分成功/部分跳过/部分失败”场景
- 下一步：
  - 进入模块 02 任务 04：实现不支持文件和空文件的 `skipped` 记录

### 2026-04-26

#### 记录 015：完成模块 02 任务 02 递归扫描行为

- 状态：已完成
- 范围：完成模块 02 中“任务 02：接入 `--recursive` 递归扫描行为”
- 结果：
  - 目录扫描函数已支持显式 `recursive` 参数
  - 默认目录导入仍保持“只扫描当前目录顶层文件”
  - 当传入 `--recursive` 时，会扫描子目录中的文件
  - 递归扫描结果仍会统一返回支持文件数、不支持文件数和文件名摘要
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 14 个测试
  - 真实目录导入示例验证成功：
    - 默认模式下 `scanned_files=1`
    - `--recursive` 模式下 `scanned_files=3`
    - `--recursive` 模式下可正确识别子目录中的支持文件与不支持文件
- 遗留问题：
  - 当前递归扫描只完成文件发现与分类，尚未接入批量导入执行
  - 目录导入总任务与文件子任务仍未落库
  - `skipped` 状态和增量跳过逻辑仍待后续任务补齐
- 下一步：
  - 进入模块 02 任务 03：实现目录导入总任务与文件子任务落库

### 2026-04-26

#### 记录 014：完成模块 02 任务 01 目录扫描与文件筛选

- 状态：已完成
- 范围：完成模块 02 中“任务 01：实现目录扫描与文件筛选”
- 结果：
  - 新增目录扫描逻辑，当前会扫描目标目录的顶层文件
  - 当前支持文件类型筛选为 `.md` 和 `.pdf`
  - 子目录当前不会被扫描，保持与“递归行为后续单独实现”的边界一致
  - 目录导入结果现在会返回扫描总数、支持文件数、不支持文件数
  - 目录导入结果会返回支持文件名列表和不支持文件名列表，便于后续验收和排查
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 12 个测试
  - 真实目录扫描示例已验证成功，返回：
    - `scanned_files=3`
    - `supported_files=2`
    - `unsupported_files=1`
- 遗留问题：
  - 当前仍未接入递归扫描
  - 当前只做扫描和筛选，尚未创建目录导入总任务或文件子任务
  - 当前只返回统计摘要，尚未触发批量单文件导入
- 下一步：
  - 进入模块 02 任务 02：接入 `--recursive` 递归扫描行为

### 2026-04-26

#### 记录 013：确定模块 02 为目录导入与增量导入 MVP

- 状态：进行中
- 范围：将第二个开发模块正式定义为“目录导入与增量导入 MVP”，在模块 01 的单文件导入闭环基础上，扩展到目录扫描、批量导入和最小增量跳过能力
- 结果：
  - 明确模块 02 不直接跳到检索、生成或前端，而是先补齐真实知识库维护所需的批量导入能力
  - 明确模块 02 的目标是“能批量导入、能识别不支持文件、能做最小增量跳过、能输出导入统计”
  - 明确模块 02 优先复用模块 01 已经打通的 Markdown 单文件导入、解析、落库和任务状态能力
- 模块目标：
  - 支持 `mindwiki import dir <path>`
  - 支持 `--recursive`
  - 扫描目录中的 `.md` 和 `.pdf`
  - 对不支持文件标记为 `skipped`
  - 基于 `content_hash` 做最小增量判断
  - 支持总任务与文件子任务的最小模型
  - 输出目录导入统计摘要
- 分步任务拆解：
  - 任务 01：实现目录扫描与文件筛选
  - 任务 02：接入 `--recursive` 递归扫描行为
  - 任务 03：实现目录导入总任务与文件子任务落库
  - 任务 04：实现不支持文件和空文件的 `skipped` 记录
  - 任务 05：实现基于 `content_hash` 的最小增量跳过
  - 任务 06：实现目录导入统计摘要输出
  - 任务 07：补充目录导入本地验收脚本
- 当前建议执行顺序：
  - 先完成目录扫描和递归控制
  - 再接总任务 / 子任务落库
  - 然后补 `skipped` 和增量跳过
  - 最后补统计输出和验收脚本
- 遗留问题：
  - PDF 当前仍未进入真实解析路径，目录导入阶段需要明确其处理策略
  - tags 当前尚未落库到 `tags/document_tags`，目录导入阶段暂时只能沿用现有输入承接
  - 总任务与子任务的汇总字段还需在实现中进一步收敛
- 下一步：
  - 开始模块 02 的任务 01：实现目录扫描与文件筛选

### 2026-04-26

#### 记录 012：完成子任务 07 最小验证测试与本地验收脚本

- 状态：已完成
- 范围：完成第一个开发模块中“任务 07：补充最小验证测试或验收脚本”
- 结果：
  - 新增 `scripts/verify_local_import.py`，用于执行最小端到端本地导入验收
  - 验收脚本会创建临时 Markdown 文件、调用 CLI 导入、查询核心表并输出 JSON 摘要
  - README 已补充最小验收脚本的运行方式与预期行为
  - `scripts/README.md` 已补充脚本用途说明
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 10 个测试
  - `PYTHONPATH=src python3 scripts/verify_local_import.py` 真实执行成功
  - 本次真实验收结果显示核心表增量为：
    - `sources +1`
    - `import_jobs +1`
    - `documents +1`
    - `sections +2`
    - `chunks +2`
- 遗留问题：
  - CLI 当前成功输出为纯文本键值串，脚本对含空格字段的解析摘要仍是近似值，不影响增量验收判断
  - 目录导入、PDF 导入、tag 落库等更完整验收场景仍待后续扩展
- 下一步：
  - 第一个开发模块的 7 个子任务已全部完成
  - 下一阶段可开始整理下一开发模块或回补剩余设计步骤

### 2026-04-26

#### 记录 011：完成子任务 06 导入任务状态流转与错误记录

- 状态：已完成
- 范围：完成第一个开发模块中“任务 06：实现导入任务状态流转与错误记录”
- 结果：
  - `import_jobs` 已接入 `pending -> running -> success/failed` 的基础状态流转
  - 导入请求开始执行前会先创建 `pending` 任务
  - 开始解析与入库前会更新为 `running`
  - 导入成功后会更新为 `success`，并写入 `started_at` 与 `finished_at`
  - 解析失败或数据库写入失败时，会尽力回写 `failed` 和 `error_message`
  - CLI 在数据库写入失败时会返回失败结果，而不是伪装成成功导入
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过，当前共 10 个测试
  - 真实 Markdown 导入已再次验证成功
  - 指定 `import_job_id = 7c3a925f-e518-4ee5-830a-df0c20de1ef7` 的数据库记录状态为 `success`
  - 该任务的 `started_at` 和 `finished_at` 已正确写入
- 遗留问题：
  - 库中保留了一条修复前留下的旧 `pending` 历史记录，后续可按需要清理
  - `skipped`、`cancelled` 和重试次数递增逻辑尚未在当前 CLI 路径完整接入
  - 目录导入的父子任务状态汇总尚未实现
- 下一步：
  - 进入任务 07：补充最小验证测试或验收脚本

### 2026-04-26

#### 记录 010：完成本地 PostgreSQL 初始化与真实导入验收

- 状态：已完成
- 范围：完成本地 PostgreSQL 环境接通、schema 初始化和真实 Markdown 导入验收
- 结果：
  - 已确认本机 `psql` 可用，路径为 PostgreSQL 16 安装目录
  - 已补项目根目录 `.env`，本地数据库连接已生效
  - 已创建本地 `mindwiki` 数据库
  - 已执行 `scripts/init_local_db.sql` 完成 schema 初始化
  - 已完成真实 Markdown 导入验收，CLI 返回 `persistence=stored`
  - 已在同一数据库上下文中验证 `sources`、`import_jobs`、`documents`、`sections`、`chunks` 均有写入记录
- 验证结果：
  - 本地真实导入成功返回 `import_job_id`、`source_id`、`document_id`
  - 验收后当前记录数为：
    - `sources = 2`
    - `import_jobs = 2`
    - `documents = 2`
    - `sections = 3`
    - `chunks = 3`
- 遗留问题：
  - tags 尚未落库到 `tags/document_tags`
  - PDF 解析与入库尚未实现
  - 导入任务状态流转仍需在任务 06 中继续完善
- 下一步：
  - 进入任务 06：实现导入任务状态流转与错误记录

### 2026-04-26

#### 记录 009：补充 PostgreSQL 本地环境配置支持

- 状态：已完成
- 范围：补充项目侧的 PostgreSQL 本地环境变量配置能力
- 结果：
  - 新增 `.env.example`，提供 `MINDWIKI_DATABASE_URL` 示例
  - 设置层支持从项目根目录 `.env` 自动读取数据库连接串
  - `.gitignore` 已忽略 `.env`
  - README 已补充 PostgreSQL 本地配置步骤，并明确 `psql` 需要单独导出环境变量
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过
  - 新增测试验证 `.env` 中的 `MINDWIKI_DATABASE_URL` 可被应用读取
- 遗留问题：
  - 当前 `.env` 还未写入真实连接串
  - 当前环境中无法直接完成本地 PostgreSQL 服务连通性验收
- 下一步：
  - 补真实 `MINDWIKI_DATABASE_URL`
  - 初始化本地 schema 并执行一次真实导入验收

### 2026-04-26

#### 记录 008：完成子任务 05 核心实体入库流程

- 状态：已完成
- 范围：完成第一个开发模块中“任务 05：实现核心实体入库流程”
- 结果：
  - 新增 PostgreSQL 导入仓储层，对接本地 `sources`、`import_jobs`、`documents`、`sections`、`chunks` 5 张核心表
  - 新增 Markdown 导入持久化流程，当前会基于解析结果写入 source、import job、document、section 和 chunk 记录
  - 导入时会生成文档内容哈希，并保存来源路径、来源备注和输入载荷
  - section 当前按 Markdown 解析结果入库，chunk 当前采用“每个有内容的 section 生成一个 chunk”的最小策略
  - 当未配置 `MINDWIKI_DATABASE_URL` 时，CLI 会明确返回 `persistence=skipped reason=database_url_missing`
  - 当仓储可用时，CLI 会返回 `import_job_id`、`source_id`、`document_id` 等持久化结果摘要
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过
  - 未配置数据库连接串时，Markdown 导入可稳定返回跳过持久化的原因
  - 通过注入式测试验证了“解析结果进入持久化层”的调用路径
- 遗留问题：
  - 当前环境未配置本地 PostgreSQL 连接串，尚未对真实数据库执行写入验收
  - tags 当前仍只保留在输入载荷中，尚未落 `tags/document_tags`
  - chunk 切分仍为最小实现，后续需要按 chunk 规则独立演进
- 下一步：
  - 进入任务 06：实现导入任务状态流转与错误记录

### 2026-04-25

#### 记录 007：完成子任务 04 Markdown 单文件读取与基础解析

- 状态：已完成
- 范围：完成第一个开发模块中“任务 04：实现 Markdown 单文件读取与基础解析”
- 结果：
  - 新增 Markdown 标准化读取逻辑，统一换行并移除 UTF-8 BOM
  - 实现简单 frontmatter 提取，当前支持基础键值和列表
  - 实现标题候选提取，当前来源包括 `frontmatter.title`、首个 H1 和文件名
  - 实现基于 Markdown 标题的 section 切分
  - 支持无标题前导正文形成匿名 section
  - 将 `.md` 文件导入入口接到解析结果，当前成功输出会返回 `title` 和 `sections` 摘要
  - 保持 `.pdf` 入口为已接入但未解析状态
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过
  - Markdown 文件导入时可返回解析后的标题和 section 数量
  - PDF 文件导入时会明确返回 `parsing=pending`
- 遗留问题：
  - frontmatter 目前只支持最小子集，尚未覆盖完整 YAML
  - 当前 section 切分仍为基础规则，尚未加入更细的结构提示与位置映射
  - 解析结果尚未写入数据库
- 下一步：
  - 进入任务 05：实现核心实体入库流程

### 2026-04-25

#### 记录 006：完成子任务 03 CLI 单文件导入入口

- 状态：已完成
- 范围：完成第一个开发模块中“任务 03：实现 `mindwiki import file <path>` 的 CLI 单文件导入入口”
- 结果：
  - 将 CLI 从纯骨架提升为可执行入口
  - 为 `import file` 补充 `--tag` 和 `--source-note` 参数
  - 为 `import dir` 补充 `--recursive`、`--tag` 和 `--source-note` 参数，保持命令接口一致
  - 在应用层新增导入请求对象，承接 CLI 参数
  - 实现单文件路径校验，包括文件是否存在、是否为文件、文件类型是否支持
  - 当前支持的单文件导入类型校验为 `.md` 和 `.pdf`
  - 完成基础错误提示与成功结果输出
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过
  - `PYTHONPATH=src python3 -m mindwiki import file <markdown-path> --tag work --source-note study` 可正常返回成功结果
  - 缺失文件场景可正常返回错误信息
- 遗留问题：
  - 当前入口只完成请求校验与参数承接，尚未进入真实 Markdown / PDF 解析
  - 当前成功结果仍属于“请求已接受”，尚未创建真实导入任务或写入数据库
- 下一步：
  - 进入任务 04：实现 Markdown 单文件读取与基础解析

### 2026-04-25

#### 记录 005：完成子任务 02 本地 PostgreSQL 初始化脚本与基础表

- 状态：已完成
- 范围：完成第一个开发模块中“任务 02：建立 PostgreSQL 本地初始化脚本与基础表”
- 结果：
  - 新增本地建表脚本 `scripts/init_local_db.sql`
  - 覆盖 5 张核心表：`sources`、`import_jobs`、`documents`、`sections`、`chunks`
  - 补充基础外键关系与常用索引
  - 新增本地重建脚本 `scripts/reset_local_db.sql`
  - 在项目说明中补充本地数据库初始化与重建命令
  - 明确 `import_jobs.status` 与 `documents.status` 的当前推荐取值
- 当前结论：
  - 当前阶段采用本地 SQL 初始化方案，不引入迁移机制
  - 状态值先按文档约定执行，暂不在 SQL 层增加强约束
- 遗留问题：
  - 尚未接入真实 PostgreSQL 写库逻辑
  - 尚未验证脚本在目标本地数据库中的实际执行结果
- 下一步：
  - 进入任务 03：实现 `mindwiki import file <path>` 的 CLI 单文件导入入口

### 2026-04-25

#### 记录 004：补充本地数据库重建脚本与状态字段约定

- 状态：已完成
- 范围：继续推进任务 02，补充本地 PostgreSQL 重建脚本，并明确核心状态字段的统一取值
- 结果：
  - 新增 `scripts/reset_local_db.sql`，支持本地开发阶段删表重建
  - 在项目说明中明确 `import_jobs.status` 与 `documents.status` 的推荐状态值
  - 保持任务 02 聚焦本地初始化方案，不引入迁移机制
- 当前状态约定：
  - `import_jobs.status`：`pending`、`running`、`success`、`failed`、`skipped`、`cancelled`
  - `documents.status`：`active`、`failed`、`deleted`
- 遗留问题：
  - 状态值目前仅在脚本和说明层面约定，尚未接入实际写库代码
  - 是否在 SQL 层增加 `CHECK` 约束，后续可根据实现稳定性再决定
- 下一步：
  - 继续完成任务 02 的收尾检查
  - 准备进入任务 03 或任务 05 的数据库接入部分

### 2026-04-25

#### 记录 003：完成子任务 01 工程骨架与目录结构初始化

- 状态：已完成
- 范围：完成第一个开发模块中“任务 01：初始化工程骨架与目录结构”
- 结果：
  - 新增基于 `Python + pyproject.toml + uv` 的项目基础配置
  - 建立 `src` 布局和分层目录结构，覆盖 `cli`、`application`、`domain`、`ingestion`、`infrastructure`
  - 预留 `mindwiki import file <path>` 与 `mindwiki import dir <path>` 的 CLI 命令入口
  - 新增本地开发所需的基础目录结构，为后续 PostgreSQL 初始化脚本预留位置
  - 新增最小测试文件，验证 CLI 参数解析
  - 完成本地最小可运行校验
- 验证结果：
  - `python3 -m pytest tests/test_cli.py` 通过
  - `PYTHONPATH=src python3 -m mindwiki --help` 可正常输出帮助信息
- 遗留问题：
  - 还未安装实际运行依赖
  - CLI 当前仅为骨架，尚未接入真实导入逻辑
  - 本地数据库初始化脚本和实体落库尚未开始
- 下一步：
  - 开始任务 02：建立 PostgreSQL 本地初始化脚本与基础表

### 2026-04-25

#### 记录 002：确定第一个开发模块为最小导入链路 MVP

- 状态：进行中
- 范围：将第一个开发模块正式定义为“最小导入链路 MVP”，以 Markdown 单文件导入为第一落地点，逐步打通 CLI、应用协调、解析、入库和任务状态追踪
- 结果：
  - 明确第一个开发模块不追求一次性完成全部能力
  - 明确首个开发目标为“先跑通最小闭环，再逐步扩展”
  - 明确该模块优先验证 Step 02、Step 03、Step 04、Step 05 的设计可落地性
- 模块目标：
  - 支持单文件导入入口
  - 支持 Markdown 解析
  - 支持 `sources`、`documents`、`sections`、`chunks`、`import_jobs` 入库
  - 支持基础任务状态流转
  - 为后续目录导入、PDF 导入、检索和生成提供稳定数据基础
- 分步任务拆解：
  - 任务 01：初始化工程骨架与目录结构
  - 任务 02：建立 PostgreSQL 本地初始化脚本与基础表
  - 任务 03：实现 `mindwiki import file <path>` 的 CLI 入口
  - 任务 04：实现 Markdown 单文件读取与基础解析
  - 任务 05：实现 `source/document/section/chunk/import_job` 写入流程
  - 任务 06：实现导入任务状态流转与错误记录
  - 任务 07：补充最小可验证测试或手工验收脚本
- 当前建议执行顺序：
  - 先完成工程骨架和数据库基础
  - 再完成 Markdown 单文件导入
  - 然后补任务状态和验收能力
  - 最后再继续扩展目录导入和 PDF
- 遗留问题：
  - 当前技术栈和目录组织尚未最终确定
  - PostgreSQL 本地初始化方式和接入细节尚未落地
  - Markdown 解析粒度需要在实现时根据实际内容再收敛
- 下一步：
  - 开始任务 01：初始化工程骨架与目录结构
  - 完成后在本文档中更新子任务状态

### 2026-04-24

#### 记录 001：初始化开发进度文档

- 状态：已完成
- 范围：新增开发进度记录文档，作为后续开发落地的统一更新入口
- 结果：
  - 明确区分设计完成与开发完成
  - 建立阶段总览表
  - 建立后续开发记录模板
- 遗留问题：
  - 各阶段开发顺序尚未最终确认
  - 具体第一批开发任务尚未登记
- 下一步：
  - 确认首个进入开发的模块
  - 完成后在本文档追加记录

---

## 后续追加模板

复制下面模板，按时间倒序追加到“开发记录”中。

```md
### YYYY-MM-DD

#### 记录 XXX：模块或阶段名称

- 状态：已完成 / 进行中 / 阻塞
- 范围：
- 结果：
- 遗留问题：
- 下一步：
```

---

## 当前开发模块拆解

### 模块 01：最小导入链路 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 初始化工程骨架与目录结构 | 已完成 | 已完成最小可运行骨架 |
| 02 | 建立 PostgreSQL 本地初始化脚本与基础表 | 已完成 | 已完成本地建表与重建脚本 |
| 03 | 实现 CLI 单文件导入入口 | 已完成 | 已支持参数承接与基础校验 |
| 04 | 实现 Markdown 单文件读取与基础解析 | 已完成 | 已支持 frontmatter、标题候选和 section 切分 |
| 05 | 实现核心实体入库流程 | 已完成 | 已接入 PostgreSQL 仓储与最小落库路径 |
| 06 | 实现导入任务状态流转与错误记录 | 已完成 | 已接入 pending/running/success/failed |
| 07 | 补充最小验证测试或验收脚本 | 已完成 | 已提供端到端本地验收脚本 |

### 模块 02：目录导入与增量导入 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 实现目录扫描与文件筛选 | 已完成 | 当前扫描目录顶层文件 |
| 02 | 接入 `--recursive` 递归扫描行为 | 已完成 | 已支持递归扫描子目录文件 |
| 03 | 实现目录导入总任务与文件子任务落库 | 已完成 | 已支持总任务和支持文件子任务创建 |
| 04 | 实现不支持文件和空文件的 `skipped` 记录 | 已完成 | 已支持 `unsupported_file_type` 和 `empty_file` |
| 05 | 实现基于 `content_hash` 的最小增量跳过 | 已完成 | 已支持 `content_unchanged` 跳过 |
| 06 | 实现目录导入统计摘要输出 | 已完成 | 已输出 `pending/skipped` 统计 |
| 07 | 补充目录导入本地验收脚本 | 已完成 | 已提供目录导入验收脚本 |

### 模块 03：目录导入执行闭环 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 批量消费目录导入中的 `pending` 子任务 | 已完成 | 已支持同命令内消费待执行子任务 |
| 02 | 复用单文件 Markdown 导入链路，完成批量真实落库 | 已完成 | 已复用既有 Markdown 导入链路和子任务 ID |
| 03 | 为暂未实现解析的 PDF 明确执行策略 | 已完成 | 当前执行阶段标记为 `pdf_parsing_not_implemented` |
| 04 | 补目录总任务执行后统计与状态汇总 | 已完成 | 已写回父任务 `execution_summary` |
| 05 | 补目录执行链路的本地验收脚本和 README 说明 | 已完成 | 已升级目录验收脚本和文档说明 |

### 模块 04：PDF 导入与解析 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 明确 PDF 第一阶段解析策略 | 已完成 | 已限定为可复制文本 PDF，按页切 section |
| 02 | 实现 PDF 单文件读取与文本提取 | 已完成 | 已接入 `pypdf` 和页级 section 提取 |
| 03 | 将 PDF 接入统一导入落库链路 | 已完成 | 已写入 `document_type=pdf` 与 `chunk.page_number` |
| 04 | 让目录导入执行阶段真正消费 PDF 子任务 | 已完成 | 已复用真实 PDF 导入链路 |
| 05 | 补 PDF 本地验收脚本与 README 说明 | 已完成 | 已升级目录 PDF 验收脚本和文档说明 |

### 模块 05：LLM 接入基础模块 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | LLM 设计对接与当前代码差异修正 | 已完成 | 已收敛第一版模块边界、目录建议与配置缺口 |
| 02 | 建立统一 `LLMRequest / LLMResponse` 协议 | 已完成 | 已完成协议模型、配置读取和最小单测 |
| 03 | 实现最小 provider 适配器 | 已完成 | 已完成 `OpenAI-compatible /chat/completions` 适配器与错误映射 |
| 04 | 实现 `generate_text` 最小可用链路 | 已完成 | 已完成 service 入口并通过真实网关 smoke test |
| 05 | 补调用生命周期控制与失败处理 | 已完成 | 已完成 retry / deadline / fallback / attempt_id |
| 06 | 补结构化输出校验与返回约定 | 已完成 | 已完成本地 JSON 解析、最小 schema 校验与问题回传 |
| 07 | 补 README、本地配置说明与验收脚本 | 已完成 | 已完成 LLM 本地验收脚本与文档闭环 |

### 模块 06：基础检索与候选召回 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 检索设计对接与当前数据结构差异修正 | 已完成 | 已收敛 chunk 主对象、可实现过滤与当前差异清单 |
| 02 | 补标签真实落库与检索侧承接 | 已完成 | 已完成 `tags / document_tags` 表与导入写入链路 |
| 03 | 明确并补第一阶段 `time_range` 时间字段承接 | 已完成 | 已确定第一阶段统一按 `documents.imported_at` 承接 |
| 04 | 补最小检索数据投影 | 已完成 | 已完成投影模型、过滤模型和 PostgreSQL 投影仓储 |
| 05 | 实现基础关键词 / BM25 召回 MVP | 已完成 | 已完成 PostgreSQL 原生全文检索与基础权重承接 |
| 06 | 实现统一 `chunk hit` 返回结构与最小过滤能力 | 已完成 | 已完成 `RetrievalService` 与统一 `chunk hit` 映射 |
| 07 | 补本地验收脚本与 README 说明 | 已完成 | 已完成检索本地验收脚本与文档闭环 |

### 模块 07：`Milvus` 向量检索基础模块 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 向量检索设计对接与当前代码差异修正 | 已完成 | 已收敛 `Milvus` 选型、边界与当前缺口 |
| 02 | 补 embedding 输入构造与版本字段承接 | 已完成 | 已补 chunk embedding 输入与版本字段写回 |
| 03 | 接入 `Milvus` 配置、客户端与 collection schema | 已完成 | 已完成本地 `Milvus` 客户端与 collection 初始化 |
| 04 | 实现 chunk 向量写入、失效与重建承接 | 已完成 | 已打通 import-time vector sync 最小闭环 |
| 05 | 实现 `vector_only` 检索仓储与候选映射 | 已完成 | 已完成向量召回仓储与候选投影映射 |
| 06 | 扩展统一检索 service，接入 `vector_only` | 已完成 | 已在统一检索入口暴露 `vector_only` |
| 07 | 补本地 `vector_only` 验收脚本与 README 说明 | 已完成 | 已完成真实本地向量检索验收闭环 |

### 模块 08：混合检索与融合排序 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 混合检索设计对接与当前代码差异修正 | 已完成 | 已收敛 `hybrid` 第一阶段范围与融合边界 |
| 02 | 扩展候选模型与融合中间结构 | 已完成 | 已新增 `HybridCandidate` 等融合承接字段 |
| 03 | 实现 `hybrid` 去重、RRF 与加权融合 | 已完成 | 已完成两路候选归并与融合打分 |
| 04 | 扩展统一检索 service，接入 `hybrid` | 已完成 | 已在统一检索入口暴露 `hybrid` |
| 05 | 补 `score_breakdown` 与排序打平规则 | 已完成 | 已补完整融合分数字段与稳定排序规则 |
| 06 | 补本地 `hybrid` 验收脚本、README 与运行说明 | 已完成 | 已完成真实本地 `hybrid` 验收闭环 |

### 模块 09：`Step 09.1-9.3` 检索编排前半段 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 检索编排设计对接与当前代码差异修正 | 已完成 | 已对齐 `9.1 / 9.2 / 9.3` 与现有检索层差距 |
| 02 | 建立 query decomposition 协议与最小实现 | 已完成 | 已完成规则优先 `decompose / none` 输出协议 |
| 03 | 实现固定三类查询扩展 | 已完成 | 已完成 `base_query / step_back_query / hyde_query` |
| 04 | 实现单个 `sub-query` 内部 4 路结果归并 | 已完成 | 已完成四路召回、去重与加权 RRF |
| 05 | 补本地验收脚本、README 与运行说明 | 已完成 | 已完成真实本地 `Step 09` 前半段验收闭环 |

### 模块 10：`Step 09.4-9.6` 检索编排后半段闭环

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 检索编排后半段设计对接与当前代码差异修正 | 已完成 | 已收敛 `SiliconFlow reranker` 方案与后半段差异清单 |
| 02 | 实现子任务级 rerank 通道 | 已完成 | 已完成独立 rerank 协议、service、provider 与 `top 5` 应用层承接 |
| 03 | 实现 context builder | 进行中 | 负责保留 `sub-query` 边界与上下文结构拼装 |
| 04 | 实现 citation payload | 未开始 | 输出面向回答层的结构化引用数据 |
| 05 | 补本地验收脚本、README 与运行说明 | 未开始 | 固化 `Step 09` 完整闭环验收入口 |
