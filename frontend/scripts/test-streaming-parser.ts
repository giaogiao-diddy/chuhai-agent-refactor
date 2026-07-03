import assert from "node:assert";
import { parseSseLines, type StreamEvent } from "../lib/streaming";

// 一个 chunk 多个 event
{
  const input = 'data: {"type":"delta","content":"你好"}\n\ndata: {"type":"done","state":{"messages":[]}}\n\n';
  const { events, rest } = parseSseLines(input);
  assert.strictEqual(events.length, 2, "multiple events in one chunk");
  assert.strictEqual(events[0].type, "delta");
  assert.strictEqual((events[0] as { content: string }).content, "你好");
  assert.strictEqual(events[1].type, "done");
  assert.strictEqual(rest, "");
}

// 半截 event：返回 rest
{
  const input = 'data: {"type":"delta","content":"你好"}\n\ndata: {"type":"d';
  const { events, rest } = parseSseLines(input);
  assert.strictEqual(events.length, 1, "only first complete event");
  assert.strictEqual(events[0].type, "delta");
  assert.ok(rest.startsWith('data: {"type":"d'), "rest contains partial line");
}

// 拼接后能解析 done
{
  const { events: ev1, rest } = parseSseLines('data: {"type":"delta","content":"x"}\n\ndata: {"type":"d');
  assert.strictEqual(ev1.length, 1);
  const { events: ev2 } = parseSseLines(rest + 'one","state":{"messages":[]}}\n\n');
  assert.strictEqual(ev2.length, 1, "second chunk resolves done");
  assert.strictEqual(ev2[0].type, "done");
}

// 无效 JSON 抛错
{
  assert.throws(() => {
    parseSseLines('data: {not valid json}\n\n');
  }, /SSE JSON parse error/);
}

// 非 data: 行忽略
{
  const { events } = parseSseLines('data: {"type":"delta","content":"x"}\n\n:keepalive\n\n');
  assert.strictEqual(events.length, 1);
}

// 空 data: 忽略
{
  const { events } = parseSseLines('data: \n\n');
  assert.strictEqual(events.length, 0);
}

// stream 结束 leftover buffer
{
  const { events, rest } = parseSseLines('data: {"type":"delta","content":"last"}\n\n');
  assert.strictEqual(events.length, 1);
  assert.strictEqual(events[0].type, "delta");
  assert.strictEqual(rest, "");
}

// ── trace event ──
{
  const input = 'data: {"type":"trace","step":"extract","status":"started"}\n\n';
  const { events } = parseSseLines(input);
  assert.strictEqual(events.length, 1);
  assert.strictEqual(events[0].type, "trace");
  assert.strictEqual((events[0] as any).step, "extract");
  assert.strictEqual((events[0] as any).status, "started");
}

// trace event with elapsed_ms and summary
{
  const input = 'data: {"type":"trace","step":"dialogue","status":"completed","elapsed_ms":1234,"summary":"已生成回复 (156 字)"}\n\n';
  const { events } = parseSseLines(input);
  assert.strictEqual(events.length, 1);
  const t = events[0] as any;
  assert.strictEqual(t.type, "trace");
  assert.strictEqual(t.elapsed_ms, 1234);
  assert.strictEqual(t.summary, "已生成回复 (156 字)");
}

// error event with state
{
  const input = 'data: {"type":"error","message":"AI 暂时不可用","state":{"messages":[],"conversation_round":1}}\n\n';
  const { events } = parseSseLines(input);
  assert.strictEqual(events.length, 1);
  const e = events[0] as any;
  assert.strictEqual(e.type, "error");
  assert.strictEqual(e.message, "AI 暂时不可用");
  assert.ok(e.state && e.state.conversation_round === 1, "error 携带 state");
}

// multi-event order preserved
{
  const input = 'data: {"type":"trace","step":"extract","status":"started"}\n\ndata: {"type":"delta","content":"你好"}\n\ndata: {"type":"trace","step":"extract","status":"completed"}\n\ndata: {"type":"done","state":{"messages":[]}}\n\n';
  const { events } = parseSseLines(input);
  assert.strictEqual(events.length, 4, "4 events");
  assert.strictEqual(events[0].type, "trace");
  assert.strictEqual(events[1].type, "delta");
  assert.strictEqual(events[2].type, "trace");
  assert.strictEqual(events[3].type, "done");
}

console.log("All parser tests passed.");
