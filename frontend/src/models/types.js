// Data models / types for RAG Law QA System

export class SearchHit {
  constructor(data) {
    this.rank = data.rank;
    this.score = data.score;
    this.source = data.source;
    this.chuong = data.chuong;
    this.dieu = data.dieu;
    this.content = data.content;
  }
}

export class Citation {
  constructor(data) {
    this.rank = data.rank;
    this.source = data.source;
    this.chuong = data.chuong;
    this.dieu = data.dieu;
    this.score = data.score;
    this.label = data.label;
  }
}

export class AskResponse {
  constructor(data) {
    this.question = data.question;
    this.backend = data.backend;
    this.chunking = data.chunking;
    this.answer = data.answer;
    this.topScore = data.top_score;
    this.grounded = data.grounded;
    this.citations = (data.citations || []).map(c => new Citation(c));
    this.sources = (data.sources || []).map(s => new SearchHit(s));
  }
}

export class SearchResponse {
  constructor(data) {
    this.query = data.query;
    this.backend = data.backend;
    this.chunking = data.chunking;
    this.count = data.count;
    this.results = (data.results || []).map(r => new SearchHit(r));
  }
}

export class LogEntry {
  constructor(data) {
    this.time = data.time;
    this.question = data.question;
    this.backend = data.backend;
    this.chunking = data.chunking;
    this.answer = data.answer;
    this.topScore = data.top_score;
    this.grounded = data.grounded;
    this.citations = (data.citations || []).map(c => new Citation(c));
    this.sources = (data.sources || []).map(s => new SearchHit(s));
  }
}
