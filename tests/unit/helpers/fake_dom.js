'use strict';

/* Faux DOM + faux jQuery minimaux pour exécuter le VRAI code de l'interface (jeedom2ha.js,
 * jeedom2ha_mapping_surface.js) sous node:vm, sans jsdom ni jQuery. Couvre uniquement ce que ce
 * code utilise : création d'éléments par chaîne HTML simple, sélecteurs composés avec
 * descendance (`.a .b[attr="v"]`), classes, attributs, propriétés, gestionnaires de clic,
 * texte/HTML échappé. Aucun comportement métier n'est simulé ici. */

function escapeText(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Comme un vrai navigateur : le texte analysé depuis du HTML est décodé (`&lt;` => `<`), si bien
// que `.text()` rend le texte d'origine et non son échappement. Story 22.2 (P3 de 20-3) : une
// assertion s'appuyait sur le texte encore échappé, comportement propre au faux DOM.
function decodeEntities(value) {
  return String(value)
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#0?39;/g, "'")
    .replace(/&amp;/g, '&');
}

class TextNode {
  constructor(text) { this.text = String(text); this.parent = null; }
}

class El {
  constructor(tag) {
    this.tag = tag;
    this.classes = new Set();
    this.attrs = {};
    this.props = {};
    this.children = [];
    this.handlers = {};
    this.parent = null;
    this.dataStore = {};
    this.visible = true;
  }
}

function textOf(node) {
  if (node instanceof TextNode) return node.text;
  return node.children.map(textOf).join('');
}

function serialize(node) {
  if (node instanceof TextNode) return escapeText(node.text);
  const cls = node.classes.size ? ` class="${[...node.classes].join(' ')}"` : '';
  return `<${node.tag}${cls}>${node.children.map(serialize).join('')}</${node.tag}>`;
}

function parseHtml(html) {
  const roots = [];
  const stack = [];
  const re = /<\/?([a-zA-Z0-9]+)((?:\s+[^>]*?)?)\s*\/?>|([^<]+)/g;
  let match;
  function add(node) {
    if (stack.length) { node.parent = stack[stack.length - 1]; stack[stack.length - 1].children.push(node); } else roots.push(node);
  }
  while ((match = re.exec(html))) {
    if (match[3] !== undefined) { add(new TextNode(decodeEntities(match[3]))); continue; }
    const whole = match[0];
    if (whole.startsWith('</')) { stack.pop(); continue; }
    const el = new El(match[1].toLowerCase());
    const attrRe = /([a-zA-Z0-9_:-]+)(?:="([^"]*)")?/g;
    let attr;
    while ((attr = attrRe.exec(match[2] || ''))) {
      if (attr[1] === 'class') (attr[2] || '').split(/\s+/).filter(Boolean).forEach((c) => el.classes.add(c));
      else el.attrs[attr[1]] = attr[2] === undefined ? '' : attr[2];
    }
    add(el);
    if (!/\/>$/.test(whole) && !['br', 'input', 'img', 'hr'].includes(el.tag)) stack.push(el);
  }
  return roots;
}

function parseCompound(compound) {
  const out = { tag: null, classes: [], attrs: [] };
  const tag = compound.match(/^[a-zA-Z][a-zA-Z0-9]*/);
  if (tag) out.tag = tag[0].toLowerCase();
  (compound.match(/\.[A-Za-z0-9_-]+/g) || []).forEach((c) => out.classes.push(c.slice(1)));
  (compound.match(/\[[^\]]+\]/g) || []).forEach((a) => {
    const m = a.match(/^\[([^=\]]+)(?:=["']?([^"'\]]*)["']?)?\]$/);
    out.attrs.push({ name: m[1], value: m[2] });
  });
  const id = compound.match(/#([A-Za-z0-9_-]+)/);
  if (id) out.attrs.push({ name: 'id', value: id[1] });
  return out;
}

function matchesCompound(el, c) {
  if (c.tag && el.tag !== c.tag) return false;
  for (const cls of c.classes) if (!el.classes.has(cls)) return false;
  for (const a of c.attrs) {
    if (!(a.name in el.attrs)) return false;
    if (a.value !== undefined && String(el.attrs[a.name]) !== a.value) return false;
  }
  return true;
}

function matchesSelector(el, selector) {
  const parts = selector.trim().split(/\s+/).map(parseCompound);
  if (!matchesCompound(el, parts[parts.length - 1])) return false;
  let node = el.parent;
  for (let i = parts.length - 2; i >= 0; i--) {
    while (node && !(node instanceof El && matchesCompound(node, parts[i]))) node = node.parent;
    if (!node) return false;
    node = node.parent;
  }
  return true;
}

function descendants(el, out) {
  out = out || [];
  el.children.forEach((child) => { if (child instanceof El) { out.push(child); descendants(child, out); } });
  return out;
}

function createDom() {
  const body = new El('body');
  const alerts = [];
  const dialogs = [];

  function wrap(list) {
    const j = Object.create(J.prototype);
    j.list = list;
    j.length = list.length;
    return j;
  }
  function J() {}
  const proto = J.prototype;
  const each = (j, fn) => { j.list.forEach(fn); return j; };
  function toNodes(arg) {
    if (arg === null || arg === undefined) return [];
    if (arg instanceof J) return arg.list;
    if (arg instanceof El || arg instanceof TextNode) return [arg];
    if (arg && typeof arg.textNode === 'string') return [new TextNode(arg.textNode)];
    if (typeof arg === 'string') return /^\s*</.test(arg) ? parseHtml(arg) : [new TextNode(arg)];
    return [];
  }

  proto.append = function (...args) {
    each(this, (el) => args.forEach((arg) => toNodes(arg).forEach((n) => { n.parent = el; el.children.push(n); })));
    return this;
  };
  proto.empty = function () { each(this, (el) => { el.children = []; }); return this; };
  proto.remove = function () {
    each(this, (el) => { if (el.parent) el.parent.children = el.parent.children.filter((c) => c !== el); el.parent = null; });
    return this;
  };
  proto.text = function (value) {
    if (value === undefined) return this.list.map(textOf).join('');
    each(this, (el) => { const t = new TextNode(value); t.parent = el; el.children = [t]; });
    return this;
  };
  proto.html = function (value) {
    if (value === undefined) return this.list.length ? this.list[0].children.map(serialize).join('') : '';
    each(this, (el) => { el.children = parseHtml(value); el.children.forEach((c) => { c.parent = el; }); });
    return this;
  };
  proto.on = function (event, first) {
    // Les gestionnaires délégués (`on(event, selector, fn)`) ne sont pas simulés.
    if (typeof first === 'function') each(this, (el) => { el.handlers[event] = first; });
    return this;
  };
  proto.one = proto.on;
  proto.off = function () { return this; };
  proto.val = function (value) {
    if (value === undefined) return this.list.length ? this.list[0].props.value : undefined;
    each(this, (el) => { el.props.value = value; });
    return this;
  };
  proto.removeData = function (key) { each(this, (el) => { delete el.dataStore[key]; }); return this; };
  proto.scrollTop = function () { return 0; };
  proto.position = function () { return { top: 0 }; };
  proto.prop = function (name, value) {
    if (value === undefined) return this.list.length ? this.list[0].props[name] : undefined;
    each(this, (el) => { el.props[name] = value; });
    return this;
  };
  proto.attr = function (name, value) {
    if (value === undefined) return this.list.length ? this.list[0].attrs[name] : undefined;
    each(this, (el) => { el.attrs[name] = String(value); });
    return this;
  };
  proto.removeAttr = function (name) { each(this, (el) => { delete el.attrs[name]; }); return this; };
  proto.addClass = function (names) {
    each(this, (el) => String(names).split(/\s+/).filter(Boolean).forEach((c) => el.classes.add(c)));
    return this;
  };
  proto.removeClass = function (names) {
    each(this, (el) => { if (names === undefined) el.classes.clear(); else String(names).split(/\s+/).forEach((c) => el.classes.delete(c)); });
    return this;
  };
  proto.hasClass = function (name) { return this.list.some((el) => el.classes.has(name)); };
  proto.data = function (key, value) {
    if (value === undefined) return this.list.length ? this.list[0].dataStore[key] : undefined;
    each(this, (el) => { el.dataStore[key] = value; });
    return this;
  };
  proto.show = function () { each(this, (el) => { el.visible = true; }); return this; };
  proto.hide = function () { each(this, (el) => { el.visible = false; }); return this; };
  proto.css = function () { return this; };
  proto.first = function () { return wrap(this.list.slice(0, 1)); };
  proto.each = function (fn) { this.list.forEach((el, i) => fn.call(wrap([el]), i, el)); return this; };
  proto.find = function (selector) {
    const found = [];
    this.list.forEach((el) => descendants(el).forEach((d) => { if (matchesSelector(d, selector)) found.push(d); }));
    return wrap(found);
  };
  proto.filter = function (selector) { return wrap(this.list.filter((el) => matchesSelector(el, selector))); };
  proto.not = function (selector) { return wrap(this.list.filter((el) => !matchesSelector(el, selector))); };
  proto.closest = function (selector) {
    const found = [];
    this.list.forEach((el) => { let n = el; while (n && !(n instanceof El && matchesSelector(n, selector))) n = n.parent; if (n) found.push(n); });
    return wrap(found.slice(0, 1));
  };
  proto.is = function (selector) { return this.list.some((el) => matchesSelector(el, selector)); };
  proto.showAlert = function (options) { alerts.push(options); return this; };
  // Story 25.1 : méthodes utilisées par le menu « ⋯ », le contrôle segmenté et l'accordéon.
  proto.prepend = function (...args) {
    each(this, (el) => args.forEach((arg) => toNodes(arg).slice().reverse().forEach((n) => { n.parent = el; el.children.unshift(n); })));
    return this;
  };
  proto.toggleClass = function (names, state) {
    each(this, (el) => String(names).split(/\s+/).filter(Boolean).forEach((c) => {
      const on = state === undefined ? !el.classes.has(c) : !!state;
      if (on) el.classes.add(c); else el.classes.delete(c);
    }));
    return this;
  };
  proto.parent = function () { return wrap(this.list.map((el) => el.parent).filter((p) => p instanceof El)); };
  proto.children = function () {
    const out = [];
    this.list.forEach((el) => el.children.forEach((c) => { if (c instanceof El) out.push(c); }));
    return wrap(out);
  };
  proto.last = function () { return wrap(this.list.slice(-1)); };
  proto.eq = function (i) { return wrap(this.list.slice(i, i + 1)); };
  proto.get = function (i) { return i === undefined ? this.list.slice() : this.list[i]; };
  proto.focus = function () { if (this.list.length) { dom.focused = this.list[0]; this.list[0].focusCount = (this.list[0].focusCount || 0) + 1; } return this; };
  proto.trigger = function (event, extra) {
    each(this, (el) => { if (el.handlers[event]) el.handlers[event].call(el, Object.assign({ target: el, preventDefault() {}, stopPropagation() {} }, extra || {})); });
    return this;
  };

  const documentEl = new El('document');
  const dom = { focused: null };
  function $(arg) {
    if (typeof arg === 'function') { arg(); return undefined; }
    if (arg === dom.document) return wrap([documentEl]);
    if (typeof arg === 'string') {
      if (/^\s*</.test(arg)) return wrap(parseHtml(arg).filter((n) => n instanceof El));
      return wrap(descendants(body).filter((el) => matchesSelector(el, arg)));
    }
    if (arg instanceof J) return arg;
    if (arg instanceof El) return wrap([arg]);
    return wrap([]);
  }
  $.ajax = () => { throw new Error('$.ajax non programmé'); };

  const bootbox = {
    dialog(options) {
      const record = { options, handlers: {}, closed: false };
      const modal = new El('div');
      modal.classes.add('modal');
      String(options.className || '').split(/\s+/).filter(Boolean).forEach((c) => modal.classes.add(c));
      const title = new El('div');
      title.classes.add('modal-title');
      parseHtml(options.title || '').forEach((n) => { n.parent = title; title.children.push(n); });
      modal.children.push(title);
      title.parent = modal;
      toNodes(options.message).forEach((n) => { n.parent = modal; modal.children.push(n); });
      modal.parent = body;
      body.children.push(modal);
      record.modal = modal;
      record.close = () => { record.closed = true; $(modal).remove(); if (record.handlers['hidden.bs.modal']) record.handlers['hidden.bs.modal'](); };
      dialogs.push(record);
      return { on(event, cb) { record.handlers[event] = cb; } };
    },
  };

  dom.document = { createTextNode: (text) => ({ textNode: String(text) }) };
  return Object.assign(dom, {
    $, body, bootbox, alerts, dialogs, documentEl,
    El, parse: parseHtml, wrap,
    add(html) { const nodes = parseHtml(html); nodes.forEach((n) => { n.parent = body; body.children.push(n); }); return $(nodes.filter((n) => n instanceof El)[0]); },
  });
}

module.exports = { createDom };
