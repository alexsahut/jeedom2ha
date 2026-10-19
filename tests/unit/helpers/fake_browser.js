'use strict';

/* Faux navigateur minimal (Story 25.4) : `location.hash`, `history` (pushState / replaceState / back / go avec
 * `popstate`), `matchMedia` (min-width / max-width), tailles de fenêtre, `addEventListener`. Suffisant pour
 * piloter le routage et la disposition de la vue C sous Node, sans rien simuler de métier. */

function createFakeWindow(options) {
  const opts = options || {};
  const listeners = {};
  const mediaLists = [];
  const win = {
    innerWidth: opts.width || 1280,
    innerHeight: opts.height || 800,
    location: { hash: opts.hash || '', pathname: '/index.php', search: '?v=d&m=jeedom2ha&p=jeedom2ha' },
    scrollY: 0,
    pageYOffset: 0,
    scrolls: [],
    scrollTo(x, y) { win.scrollY = y; win.pageYOffset = y; win.scrolls.push(y); },
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener(type, fn) { listeners[type] = (listeners[type] || []).filter((f) => f !== fn); },
    dispatch(type, event) { (listeners[type] || []).slice().forEach((fn) => fn(Object.assign({ type }, event || {}))); },
    listenerCount(type) { return (listeners[type] || []).length; },
  };

  const entries = [{ hash: win.location.hash, state: null }];
  let index = 0;
  const writes = { push: 0, replace: 0 };
  function hashOf(url) {
    const at = String(url == null ? '' : url).indexOf('#');
    return at === -1 ? '' : String(url).slice(at);
  }
  win.history = {
    get state() { return entries[index].state; },
    get length() { return entries.length; },
    pushState(state, _title, url) {
      entries.splice(index + 1);
      entries.push({ hash: url == null ? win.location.hash : hashOf(url), state });
      index += 1;
      win.location.hash = entries[index].hash;
      writes.push += 1;
    },
    replaceState(state, _title, url) {
      entries[index] = { hash: url == null ? win.location.hash : hashOf(url), state };
      win.location.hash = entries[index].hash;
      writes.replace += 1;
    },
    go(delta) {
      const target = index + delta;
      if (target < 0 || target >= entries.length) return;
      index = target;
      win.location.hash = entries[index].hash;
      win.dispatch('popstate', { state: entries[index].state });
    },
    back() { win.history.go(-1); },
    forward() { win.history.go(1); },
  };

  function evaluate(query) {
    const min = /\(min-width:\s*([0-9.]+)px\)/.exec(query);
    const max = /\(max-width:\s*([0-9.]+)px\)/.exec(query);
    return (!min || win.innerWidth >= Number(min[1])) && (!max || win.innerWidth <= Number(max[1]));
  }
  win.matchMedia = opts.noMatchMedia ? undefined : function matchMedia(query) {
    const handlers = [];
    const mql = {
      media: query,
      get matches() { return evaluate(query); },
      addEventListener(_t, fn) { handlers.push(fn); },
      removeEventListener(_t, fn) { handlers.splice(handlers.indexOf(fn), 1); },
      addListener(fn) { handlers.push(fn); },
      removeListener(fn) { handlers.splice(handlers.indexOf(fn), 1); },
      fire() { handlers.slice().forEach((fn) => fn({ matches: evaluate(query), media: query })); },
    };
    mediaLists.push(mql);
    return mql;
  };
  win.setSize = function setSize(width, height) {
    win.innerWidth = width;
    if (height) win.innerHeight = height;
    mediaLists.forEach((mql) => mql.fire());
    win.dispatch('resize');
  };
  win.rotate = function rotate() {
    const width = win.innerWidth;
    win.setSize(win.innerHeight, width);
    win.dispatch('orientationchange');
  };
  win.historyWrites = writes;
  win.historyEntries = entries;
  win.historyIndex = () => index;
  win.sessionStorage = (function storage() {
    const data = {};
    return {
      getItem: (k) => (Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null),
      setItem: (k, v) => { data[k] = String(v); },
      removeItem: (k) => { delete data[k]; },
    };
  }());
  return win;
}

module.exports = { createFakeWindow };
