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

### 2026-04-28

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

### 模块 05：检索前置能力对齐 MVP

| 任务 | 内容 | 状态 | 备注 |
| --- | --- | --- | --- |
| 01 | 检索设计对接与差异修正 | 已完成 | 已收敛模块 05 当前阶段边界与差异清单 |
| 02 | 补标签真实落库与文档级标签承接 | 未开始 | 为 `document_tags` 命中能力补数据基础 |
| 03 | 补最小定位信息持久化 | 未开始 | 优先补 Markdown 与 PDF 的最小定位承接 |
| 04 | 补统一检索结果所需的最小数据投影 | 未开始 | 为 `chunk hit` / citation payload 做数据准备 |
| 05 | 补检索前置能力的本地验收脚本与 README 说明 | 未开始 | 支撑后续回归验证 |
