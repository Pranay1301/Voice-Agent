const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');
const config = require('./env');
const { createLogger } = require('../utils/logger');
const logger = createLogger('database');

const dbPath = config.DATABASE_PATH || './data/voice_agent.db';
const dbDir = path.dirname(path.resolve(dbPath));

if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');

// Initialize tables
db.exec(`
CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  name TEXT,
  phone TEXT,
  email TEXT,
  language TEXT,
  lead_temperature TEXT DEFAULT 'UNKNOWN',
  budget TEXT,
  budget_numeric REAL,
  location TEXT,
  requirements TEXT,
  timeline TEXT,
  decision_maker TEXT,
  intent_score REAL DEFAULT 0,
  status TEXT DEFAULT 'new',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS calls (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  twilio_call_sid TEXT,
  started_at TEXT,
  ended_at TEXT,
  duration INTEGER,
  transcript TEXT,
  summary TEXT,
  language TEXT,
  status TEXT DEFAULT 'pending',
  metadata TEXT,
  FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS conversation_state (
  call_id TEXT PRIMARY KEY,
  structured_state TEXT,
  current_intent TEXT,
  confidence REAL DEFAULT 0,
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (call_id) REFERENCES calls(id)
);

CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  call_id TEXT,
  type TEXT,
  status TEXT DEFAULT 'pending',
  payload TEXT,
  idempotency_key TEXT UNIQUE,
  created_at TEXT DEFAULT (datetime('now')),
  executed_at TEXT,
  error TEXT,
  FOREIGN KEY (call_id) REFERENCES calls(id)
);

CREATE TABLE IF NOT EXISTS followups (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  channel TEXT,
  content TEXT,
  scheduled_at TEXT,
  sent_at TEXT,
  status TEXT DEFAULT 'pending',
  FOREIGN KEY (lead_id) REFERENCES leads(id)
);
`);

// Helper functions
function insertLead(lead) {
  const stmt = db.prepare(`
    INSERT INTO leads (id, name, phone, email, language, lead_temperature, budget, budget_numeric, location, requirements, timeline, decision_maker, intent_score, status)
    VALUES (@id, @name, @phone, @email, @language, @lead_temperature, @budget, @budget_numeric, @location, @requirements, @timeline, @decision_maker, @intent_score, @status)
    ON CONFLICT(id) DO UPDATE SET
      name=coalesce(@name, name),
      phone=coalesce(@phone, phone),
      email=coalesce(@email, email),
      language=coalesce(@language, language),
      lead_temperature=coalesce(@lead_temperature, lead_temperature),
      budget=coalesce(@budget, budget),
      budget_numeric=coalesce(@budget_numeric, budget_numeric),
      location=coalesce(@location, location),
      requirements=coalesce(@requirements, requirements),
      timeline=coalesce(@timeline, timeline),
      decision_maker=coalesce(@decision_maker, decision_maker),
      intent_score=coalesce(@intent_score, intent_score),
      status=coalesce(@status, status),
      updated_at=datetime('now')
  `);
  return stmt.run(lead);
}

function updateLead(id, updates) {
  const fields = Object.keys(updates).map(k => `${k} = @${k}`).join(', ');
  const stmt = db.prepare(`UPDATE leads SET ${fields}, updated_at = datetime('now') WHERE id = @id`);
  return stmt.run({ ...updates, id });
}

function getLead(id) {
  return db.prepare('SELECT * FROM leads WHERE id = ?').get(id);
}

function getLeadByPhone(phone) {
  return db.prepare('SELECT * FROM leads WHERE phone = ?').get(phone);
}

function getLeads(limit = 50) {
  return db.prepare('SELECT * FROM leads ORDER BY created_at DESC LIMIT ?').all(limit);
}

function insertCall(call) {
  const stmt = db.prepare(`
    INSERT INTO calls (id, lead_id, twilio_call_sid, started_at, ended_at, duration, transcript, summary, language, status, metadata)
    VALUES (@id, @lead_id, @twilio_call_sid, @started_at, @ended_at, @duration, @transcript, @summary, @language, @status, @metadata)
  `);
  return stmt.run({
    id: call.id,
    lead_id: call.lead_id || null,
    twilio_call_sid: call.twilio_call_sid || null,
    started_at: call.started_at || new Date().toISOString(),
    ended_at: call.ended_at || null,
    duration: call.duration || 0,
    transcript: typeof call.transcript === 'object' ? JSON.stringify(call.transcript) : call.transcript || '',
    summary: call.summary || '',
    language: call.language || 'en',
    status: call.status || 'pending',
    metadata: typeof call.metadata === 'object' ? JSON.stringify(call.metadata) : call.metadata || '{}'
  });
}

function updateCall(id, updates) {
  const params = { id };
  const clauses = [];
  for (const [k, v] of Object.entries(updates)) {
    clauses.push(`${k} = @${k}`);
    params[k] = (typeof v === 'object' && v !== null) ? JSON.stringify(v) : v;
  }
  if (clauses.length === 0) return;
  const stmt = db.prepare(`UPDATE calls SET ${clauses.join(', ')} WHERE id = @id`);
  return stmt.run(params);
}

function getCall(id) {
  return db.prepare('SELECT * FROM calls WHERE id = ? OR twilio_call_sid = ?').get(id, id);
}

function getCalls(limit = 20) {
  return db.prepare('SELECT * FROM calls ORDER BY started_at DESC LIMIT ?').all(limit);
}

function insertAction(action) {
  const stmt = db.prepare(`
    INSERT INTO actions (id, call_id, type, status, payload, idempotency_key)
    VALUES (@id, @call_id, @type, @status, @payload, @idempotency_key)
  `);
  return stmt.run({
    id: action.id,
    call_id: action.call_id,
    type: action.type,
    status: action.status || 'pending',
    payload: typeof action.payload === 'object' ? JSON.stringify(action.payload) : action.payload,
    idempotency_key: action.idempotency_key || null
  });
}

function updateAction(id, updates) {
  const params = { id };
  const clauses = [];
  for (const [k, v] of Object.entries(updates)) {
    clauses.push(`${k} = @${k}`);
    params[k] = (typeof v === 'object' && v !== null) ? JSON.stringify(v) : v;
  }
  if (clauses.length === 0) return;
  const stmt = db.prepare(`UPDATE actions SET ${clauses.join(', ')} WHERE id = @id`);
  return stmt.run(params);
}

function getAction(idOrKey) {
  return db.prepare('SELECT * FROM actions WHERE id = ? OR idempotency_key = ?').get(idOrKey, idOrKey);
}

function getActionsByCallId(callId) {
  return db.prepare('SELECT * FROM actions WHERE call_id = ? ORDER BY created_at ASC').all(callId);
}

function insertFollowup(followup) {
  const stmt = db.prepare(`
    INSERT INTO followups (id, lead_id, channel, content, scheduled_at, status)
    VALUES (@id, @lead_id, @channel, @content, @scheduled_at, @status)
  `);
  return stmt.run(followup);
}

function saveConversationState(callId, structuredState, currentIntent, confidence) {
  const stmt = db.prepare(`
    INSERT INTO conversation_state (call_id, structured_state, current_intent, confidence, updated_at)
    VALUES (@call_id, @structured_state, @current_intent, @confidence, datetime('now'))
    ON CONFLICT(call_id) DO UPDATE SET
      structured_state = @structured_state,
      current_intent = @current_intent,
      confidence = @confidence,
      updated_at = datetime('now')
  `);
  return stmt.run({
    call_id: callId,
    structured_state: typeof structuredState === 'object' ? JSON.stringify(structuredState) : structuredState,
    current_intent: currentIntent || 'unknown',
    confidence: confidence || 0
  });
}

function getConversationState(callId) {
  return db.prepare('SELECT * FROM conversation_state WHERE call_id = ?').get(callId);
}

module.exports = {
  db,
  insertLead,
  updateLead,
  getLead,
  getLeadByPhone,
  getLeads,
  insertCall,
  updateCall,
  getCall,
  getCalls,
  insertAction,
  updateAction,
  getAction,
  getActionsByCallId,
  insertFollowup,
  saveConversationState,
  getConversationState
};
