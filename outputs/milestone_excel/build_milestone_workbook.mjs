import fs from "node:fs/promises";
import path from "node:path";

import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("final");
const outputPath = path.join(outputDir, "项目里程碑计划.xlsx");

const headers = [
  "里程碑",
  "开始时间",
  "预计完成",
  "当前状态",
  "我的工作内容",
  "需开发A配合",
  "交付物",
];

const rows = [
  [
    "M0 环境搭建",
    "6月17日",
    "6月17日",
    "✅ 已完成",
    "1. 创建 CloudBase 云开发环境\n2. 开通 8 个云数据库集合\n3. 部署 11 个云函数\n4. 编写前后端接口契约文档（API_CONTRACT.md）",
    "提供小程序 AppID 和项目框架",
    "可运行的小程序骨架 + 云端环境就绪",
  ],
  [
    "M1 数据模型",
    "6月17日",
    "6月18日",
    "进行中",
    "1. 创建题目、顾问备注、系统配置 3 个新集合\n2. 设计每道题的数据结构（题型、选项、评分规则）\n3. 和开发A对齐答案提交格式、报告返回格式",
    "确认题目字段结构是否满足前端展示需求",
    "数据库集合创建完成 + 接口数据结构文档定稿",
  ],
  [
    "M2 基础接口",
    "6月18日",
    "6月18日",
    "待开始",
    "1. 编写微信登录云函数，返回用户身份（普通用户/顾问/管理员）\n2. 编写系统配置云函数，返回客服微信二维码等全局配置\n3. 编写管理员修改配置的云函数",
    "确认登录流程：是否需要弹窗授权，以及首页入口逻辑",
    "login / getSystemConfig / updateSystemConfig 三个接口可用",
  ],
  [
    "M3 题库与测评",
    "6月18日",
    "6月19日",
    "待开始",
    "1. 将完整题库导入云数据库\n2. 为每道题目配置企业出海评分规则和顾问跟进评分规则\n3. 编写获取测评配置的云函数（返回题目、选项、分层规则）\n4. 编写创建测评的云函数（保存企业基础信息）",
    "提供 18+ 道题目的完整文案、选项内容和分层逻辑",
    "题目数据入库 + getAssessmentConfig / createAssessment 接口可用",
  ],
  [
    "M4 答题与评分",
    "6月19日",
    "6月20日",
    "待开始",
    "1. 实现答题实时保存功能\n2. 实现分层逻辑（有外贸经验/无外贸经验两套题）\n3. 实现双评分引擎：企业出海评分（0-100分）+ 顾问跟进评分（0-100分）\n4. 实现标签生成逻辑（高潜力出海企业、A类客户等）\n5. 编写提交测评的云函数（提交→算分→触发报告生成）",
    "1. 答题页支持单选、多选、填空、说明四种题型\n2. 根据分层结果展示不同题目\n3. 提交后显示加载页，轮询报告状态",
    "submitAssessment 接口可用 + 评分系统验证通过",
  ],
  [
    "M5 报告生成",
    "6月20日",
    "6月22日",
    "待开始",
    "1. 接入 DeepSeek AI 生成三类报告：\n   - 部分分析报告（用户免费看）\n   - 完整分析报告（18个章节）\n   - 顾问跟进报告（销售话术、跟进建议）\n2. 编写 AI 失败时的模板兜底逻辑\n3. 编写获取用户报告的云函数（未解锁时只返回部分内容，已解锁返回全部）",
    "1. 报告展示页设计\n2. 部分报告页和完整报告预览页的开发\n3. 完整报告详情页的开发",
    "三类报告生成逻辑就绪 + AI失败有兜底",
  ],
  [
    "M6 解锁与顾问端",
    "6月22日",
    "6月23日",
    "待开始",
    "1. 编写添加客服微信后自动解锁完整报告的云函数\n2. 编写顾问端用户列表云函数（支持筛选、搜索、分页）\n3. 编写顾问查看用户详情云函数（含答题记录、评分、报告、跟进状态）\n4. 编写顾问跟进状态和备注的云函数",
    "1. 客服微信解锁页面\n2. 顾问端全部页面（列表、详情、跟进管理）\n3. 权限区分：普通用户看不到顾问评分的页面",
    "解锁链路完整可用 + 顾问端数据接口就绪",
  ],
  [
    "M7 联调验收",
    "6月23日",
    "6月25日",
    "待开始",
    "1. 逐接口验证用户端完整链路\n2. 逐接口验证顾问端完整链路\n3. 校验所有权限（用户不能看到顾问数据）\n4. 处理异常状态（报告生成失败、未解锁等）",
    "1. 逐页面接入真实接口\n2. UI细节完善\n3. 真机测试",
    "全部验收标准通过 + 可提审版本",
  ],
];

const statusCounts = rows.reduce((acc, row) => {
  acc[row[3]] = (acc[row[3]] ?? 0) + 1;
  return acc;
}, {});

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("项目里程碑");

sheet.getRange("A1:G1").merge();
sheet.getRange("A1").values = [["项目里程碑计划"]];
sheet.getRange("A2:G2").merge();
sheet.getRange("A2").values = [["CloudBase 小程序测评系统｜M0-M7 排期与协作事项"]];

sheet.getRange("A4:B7").values = [
  ["总里程碑", rows.length],
  ["已完成", statusCounts["✅ 已完成"] ?? 0],
  ["进行中", statusCounts["进行中"] ?? 0],
  ["待开始", statusCounts["待开始"] ?? 0],
];

sheet.getRange("D4:G7").values = [
  ["计划周期", "6月17日 - 6月25日", "当前重点", "M1 数据模型"],
  ["后端职责", "云函数、数据库、评分、报告", "前端职责", "小程序页面、联调、真机测试"],
  ["关键依赖", "题库文案、AppID、页面交互确认", "验收目标", "可提审版本"],
  ["备注", "状态可在表格中继续更新", "", ""],
];

sheet.getRange("A9:G9").values = [headers];
sheet.getRange(`A10:G${9 + rows.length}`).values = rows;

sheet.getRange("A1:G2").format = {
  fill: "#16324F",
  font: { name: "Microsoft YaHei", color: "#FFFFFF", bold: true },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
sheet.getRange("A1").format.font = { size: 18, bold: true, color: "#FFFFFF" };
sheet.getRange("A2").format.font = { size: 11, color: "#D8E6F3" };

sheet.getRange("A4:B7").format = {
  fill: "#F4F8FB",
  font: { name: "Microsoft YaHei", size: 10, color: "#243447" },
  borders: { preset: "all", style: "thin", color: "#CFD8E3" },
  verticalAlignment: "center",
};
sheet.getRange("A4:A7").format.font = { bold: true, color: "#16324F" };
sheet.getRange("B4:B7").format = {
  horizontalAlignment: "center",
  font: { name: "Microsoft YaHei", size: 11, bold: true, color: "#0F766E" },
};

sheet.getRange("D4:G7").format = {
  fill: "#FAFBFC",
  font: { name: "Microsoft YaHei", size: 10, color: "#243447" },
  borders: { preset: "all", style: "thin", color: "#CFD8E3" },
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange("D4:D7").format.font = { bold: true, color: "#16324F" };
sheet.getRange("F4:F7").format.font = { bold: true, color: "#16324F" };

sheet.getRange("A9:G9").format = {
  fill: "#2F5D7C",
  font: { name: "Microsoft YaHei", size: 10, color: "#FFFFFF", bold: true },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#AFC2D2" },
};

const bodyRange = sheet.getRange(`A10:G${9 + rows.length}`);
bodyRange.format = {
  font: { name: "Microsoft YaHei", size: 10, color: "#1F2933" },
  verticalAlignment: "top",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#DFE7EF" },
};

for (let i = 0; i < rows.length; i += 1) {
  const rowNumber = 10 + i;
  const fill = i % 2 === 0 ? "#FFFFFF" : "#F8FAFC";
  sheet.getRange(`A${rowNumber}:G${rowNumber}`).format.fill = fill;
}

sheet.getRange("A10:A17").format.font = { bold: true, color: "#16324F" };
sheet.getRange("B10:D17").format.horizontalAlignment = "center";
sheet.getRange("D10:D17").format.font = { bold: true };

sheet.getRange("D10").format.fill = "#DCFCE7";
sheet.getRange("D10").format.font = { color: "#166534", bold: true };
sheet.getRange("D11").format.fill = "#FEF3C7";
sheet.getRange("D11").format.font = { color: "#92400E", bold: true };
sheet.getRange("D12:D17").format.fill = "#EEF2FF";
sheet.getRange("D12:D17").format.font = { color: "#3730A3", bold: true };

sheet.getRange("A:G").format.autofitColumns();
sheet.getRange("A1:G17").format.autofitRows();

sheet.getRange("A:A").format.columnWidthPx = 130;
sheet.getRange("B:C").format.columnWidthPx = 92;
sheet.getRange("D:D").format.columnWidthPx = 92;
sheet.getRange("E:E").format.columnWidthPx = 420;
sheet.getRange("F:F").format.columnWidthPx = 310;
sheet.getRange("G:G").format.columnWidthPx = 280;

sheet.getRange("1:1").format.rowHeightPx = 34;
sheet.getRange("2:2").format.rowHeightPx = 24;
sheet.getRange("9:9").format.rowHeightPx = 30;
sheet.getRange("10:17").format.rowHeightPx = 110;

sheet.freezePanes.freezeRows(9);
sheet.showGridlines = false;

const usedRange = sheet.getRange("A1:G17");
usedRange.format.borders = { preset: "outside", style: "medium", color: "#91A9BD" };

const inspect = await workbook.inspect({
  kind: "table",
  range: "项目里程碑!A1:G17",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await workbook.render({ sheetName: "项目里程碑", range: "A1:G17", scale: 1 });

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

console.log(`Saved ${outputPath}`);
