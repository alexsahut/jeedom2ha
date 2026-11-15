// Front v3 (Lot 6) : info-bulles ⓘ qui fonctionnent, `window.Jeedom2haInfoTip`.
// Un seul composant pour toute l'aide du plugin : la page (maison, pièce, fiche, panneaux, guide, scénarios) et la
// configuration du plugin. L'aide ne dépend plus de l'attribut `title` (délai du navigateur, interception par le cœur, aucun
// survol sur tablette) : un clic, un toucher ou Entrée / Espace ouvre une bulle ancrée à l'icône, posée sur `body`.
//
// Deux déclencheurs :
// - `.j2ha-info` : l'icône ⓘ, un vrai <button>, texte dans `data-j2ha-tip`, nom accessible « Aide : … » (rendu par `button`) ;
// - `.j2ha-tip` : une pastille ou une marque purement informative (barre d'état, compteurs…) ; son `title` reste en complément,
//   le texte de la bulle est `data-j2ha-tip`, sinon son `title` courant (rendu focusable et cliquable par `attach`).
// Option `data-j2ha-doc="<ancre>"` : lien « En savoir plus » vers cette ancre de la documentation du plugin (lien « Aide » de la
// page, ou `data-j2ha-doc-base` posé par la configuration), seulement si l'adresse de la documentation est connue.
//
// Fermeture : second clic, Échap (le focus revient à l'icône), clic ailleurs, ouverture d'une autre bulle (une seule à la fois).
// Survol à la souris : ouverture après 300 ms, fermeture à la sortie ; le clic reste le mode garanti. Aucune dépendance : ni
// Bootstrap, ni jQuery UI, ni tooltipster ; `button` et `attach` reçoivent le jQuery de l'appelant. Chargeable sous node.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  // Chargé deux fois (configuration rouverte) : le premier composant reste, ses écouteurs ne sont pas doublés.
  if (root.Jeedom2haInfoTip && root.Jeedom2haInfoTip.install) return;
  root.Jeedom2haInfoTip = factory();
  if (typeof document !== 'undefined' && document.addEventListener) root.Jeedom2haInfoTip.install(document);
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var TRIGGERS = '.j2ha-info, .j2ha-tip';
  var INTERACTIVE = 'a, button, input, select, textarea, label, [role="button"], [role="menuitem"]';
  var HOVER_OPEN_MS = 300;
  var HOVER_CLOSE_MS = 150;
  var MARGIN = 8;
  var GAP = 8;

  // --- Rendu (appelé par les modules de la page avec leur jQuery) ---

  /** ⓘ : `<button type="button" class="j2ha-info">` ; `opts` = { cls, doc (ancre), label (nom accessible, sinon le texte) }. */
  function button($, text, opts) {
    var o = opts || {};
    var tip = String(text || '');
    var $b = $('<button type="button" class="j2ha-info j2ha-v3-info"></button>')
      .attr('data-j2ha-tip', tip)
      .attr('aria-label', '{{Aide}} : ' + (o.label || tip))
      .attr('aria-expanded', 'false')
      .append($('<i class="fas fa-info-circle" aria-hidden="true"></i>'));
    if (o.cls) $b.addClass(o.cls);
    if (o.doc) $b.attr('data-j2ha-doc', o.doc);
    return $b;
  }

  /** Pastille informative : focusable, cliquable, ouvre la même bulle. Son `title` passe dans `data-j2ha-tip` et disparaît
   *  (sinon l'info-bulle du navigateur, ou celle du cœur Jeedom 4.4+, double la bulle) ; `aria-label` reste le nom accessible. */
  function attach($el, text, opts) {
    var o = opts || {};
    if (!$el || !$el.length) return $el;
    $el.addClass('j2ha-tip j2ha-v3-tip').attr('aria-expanded', 'false');
    var tip = text !== undefined && text !== null ? String(text) : $el.attr('title');
    if (tip !== undefined && tip !== null && tip !== '') {
      $el.attr('data-j2ha-tip', tip);
      if ($el.attr('aria-label') === undefined) $el.attr('aria-label', tip);
    }
    $el.removeAttr('title');
    if ($el.attr('tabindex') === undefined) $el.attr('tabindex', '0');
    $el.attr('role', 'button');
    if (o.doc) $el.attr('data-j2ha-doc', o.doc);
    return $el;
  }

  // --- Comportement (navigateur seulement) ---

  var state = { doc: null, open: null, seq: 0, hoverTimer: null, closeTimer: null };

  function closestTrigger(target) {
    if (!target || !target.closest) return null;
    var trigger = target.closest(TRIGGERS);
    if (!trigger) return null;
    // Un bouton, un lien ou un champ DANS une pastille garde son action (ex. « Relire » à côté d'un mot).
    var inner = target.closest(INTERACTIVE);
    if (inner && inner !== trigger && trigger.contains(inner)) return null;
    return trigger;
  }

  function tipText(el) {
    var keys = ['data-j2ha-tip', 'title', 'data-j2ha-title', 'data-title', 'data-original-title', 'aria-label'];
    for (var i = 0; i < keys.length; i++) {
      var v = el.getAttribute(keys[i]);
      if (typeof v === 'string' && v.trim() !== '') return v.trim();
    }
    return '';
  }

  // Le `title` d'une pastille est mis de côté pendant le survol et l'ouverture (sinon l'info-bulle du navigateur double la
  // bulle), puis rendu ; s'il a été réécrit entre-temps (état rafraîchi), la nouvelle valeur gagne.
  function stashTitle(el) {
    var t = el.getAttribute('title');
    if (t === null) return;
    el.setAttribute('data-j2ha-title', t);
    el.removeAttribute('title');
  }
  function restoreTitle(el) {
    var t = el.getAttribute('data-j2ha-title');
    if (t === null) return;
    el.removeAttribute('data-j2ha-title');
    if (el.getAttribute('title') === null) el.setAttribute('title', t);
  }

  function docBase(doc) {
    var candidates = doc.querySelectorAll('a.j2ha-v3-help[href], [data-j2ha-doc-base]');
    for (var i = 0; i < candidates.length; i++) {
      var href = candidates[i].getAttribute('data-j2ha-doc-base') || candidates[i].getAttribute('href') || '';
      if (href.indexOf('https://') === 0) return href.split('#')[0];
    }
    return null;
  }

  function clearTimers() {
    if (state.hoverTimer) { clearTimeout(state.hoverTimer); state.hoverTimer = null; }
    if (state.closeTimer) { clearTimeout(state.closeTimer); state.closeTimer = null; }
  }

  function place(pop, trigger) {
    var win = state.doc.defaultView;
    var vw = state.doc.documentElement.clientWidth || win.innerWidth;
    var vh = state.doc.documentElement.clientHeight || win.innerHeight;
    var r = trigger.getBoundingClientRect();
    pop.style.maxWidth = Math.max(120, Math.min(320, vw - 2 * MARGIN)) + 'px';
    pop.style.left = '0px';
    pop.style.top = '0px';
    var w = pop.offsetWidth;
    var h = pop.offsetHeight;
    var center = r.left + r.width / 2;
    var left = Math.round(Math.min(Math.max(center - w / 2, MARGIN), Math.max(MARGIN, vw - w - MARGIN)));
    var below = r.bottom + GAP;
    var above = r.top - GAP - h;
    var side = (below + h <= vh - MARGIN || above < MARGIN) ? 'below' : 'above';
    var top = side === 'below' ? below : above;
    top = Math.round(Math.min(Math.max(top, MARGIN), Math.max(MARGIN, vh - h - MARGIN)));
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
    pop.setAttribute('data-side', side);
    var arrow = pop.querySelector('.j2ha-info-pop-arrow');
    if (arrow) arrow.style.left = Math.round(Math.min(Math.max(center - left, 12), w - 12)) + 'px';
  }

  function close(focusBack) {
    clearTimers();
    var cur = state.open;
    if (!cur) return;
    state.open = null;
    if (cur.pop.parentNode) cur.pop.parentNode.removeChild(cur.pop);
    cur.trigger.setAttribute('aria-expanded', 'false');
    cur.trigger.removeAttribute('aria-describedby');
    cur.trigger.classList.remove('is-open');
    restoreTitle(cur.trigger);
    if (focusBack && cur.trigger.focus) cur.trigger.focus();
  }

  function open(trigger, mode) {
    clearTimers();
    if (state.open && state.open.trigger === trigger) {
      if (mode === 'pinned') state.open.mode = 'pinned';
      return state.open;
    }
    close(false);
    var doc = state.doc;
    var text = tipText(trigger);
    if (!text) return null;
    stashTitle(trigger);
    state.seq += 1;
    var pop = doc.createElement('div');
    pop.className = 'j2ha-info-pop j2ha-v3-pop';
    pop.id = 'j2ha-info-pop-' + state.seq;
    pop.setAttribute('role', 'tooltip');
    var body = doc.createElement('span');
    body.className = 'j2ha-info-pop-text';
    body.textContent = text;
    pop.appendChild(body);
    var anchor = trigger.getAttribute('data-j2ha-doc');
    var base = anchor ? docBase(doc) : null;
    if (anchor && base) {
      var more = doc.createElement('a');
      more.className = 'j2ha-info-more j2ha-v3-pop-more';
      more.setAttribute('href', base + '#' + anchor.replace(/^#/, ''));
      more.setAttribute('target', '_blank');
      more.setAttribute('rel', 'noopener');
      more.textContent = '{{En savoir plus}}';
      pop.appendChild(doc.createTextNode(' '));
      pop.appendChild(more);
    }
    var arrow = doc.createElement('span');
    arrow.className = 'j2ha-info-pop-arrow j2ha-v3-pop-arrow';
    arrow.setAttribute('aria-hidden', 'true');
    pop.appendChild(arrow);
    // Posée sur `body` (jamais rognée par un conteneur en overflow: hidden), créée à chaque ouverture : elle n'hérite pas de
    // l'attribut `inert` posé sur le reste de la page par la fenêtre « Corriger le type ».
    doc.body.appendChild(pop);
    trigger.setAttribute('aria-expanded', 'true');
    trigger.setAttribute('aria-describedby', pop.id);
    trigger.classList.add('is-open');
    state.open = { trigger: trigger, pop: pop, mode: mode };
    place(pop, trigger);
    return state.open;
  }

  function onClick(event) {
    var trigger = closestTrigger(event.target);
    if (trigger) {
      // Le clic sur l'aide ne déclenche jamais l'action d'un parent (ligne, étiquette, tuile).
      event.preventDefault();
      event.stopPropagation();
      if (state.open && state.open.trigger === trigger && state.open.mode === 'pinned') close(false);
      else open(trigger, 'pinned');
      return;
    }
    if (state.open && !state.open.pop.contains(event.target)) close(false);
  }

  function onKeydown(event) {
    var key = event.key;
    if (key === 'Escape' && state.open) {
      // Échap ferme d'abord la bulle (ni la fenêtre, ni le menu, ni la pièce derrière elle).
      event.preventDefault();
      event.stopPropagation();
      close(true);
      return;
    }
    var trigger = closestTrigger(event.target);
    if (trigger && event.target === trigger && (key === 'Enter' || key === ' ' || key === 'Spacebar')) {
      // Un <button> natif transforme déjà Entrée / Espace en clic ; une pastille (role="button") est ouverte ici.
      if (trigger.tagName === 'BUTTON') return;
      event.preventDefault();
      event.stopPropagation();
      if (state.open && state.open.trigger === trigger && state.open.mode === 'pinned') close(false);
      else open(trigger, 'pinned');
      return;
    }
    if (key === 'Tab' && state.open) {
      var more = state.open.pop.querySelector('a');
      if (event.target === state.open.trigger && more && !event.shiftKey) {
        // Le lien « En savoir plus » de la bulle suit l'icône dans l'ordre du clavier. La touche ne va pas plus loin : le piège
        // de focus d'une fenêtre (« Corriger le type ») ramènerait sinon le focus dans la fenêtre, hors de la bulle.
        event.preventDefault();
        event.stopPropagation();
        more.focus();
        return;
      }
      if (state.open.pop.contains(event.target)) {
        event.preventDefault();
        event.stopPropagation();
        close(true);
        return;
      }
      close(false);
    }
  }

  // Le focus dans la bulle (posée sur body) n'est pas « hors de la fenêtre » : le rappel de focus d'une modale Bootstrap / bootbox
  // (`focusin` sur document) ne doit pas le reprendre.
  function onFocusIn(event) {
    if (state.open && state.open.pop.contains(event.target)) event.stopPropagation();
  }

  function isMouse(event) { return !event.pointerType || event.pointerType === 'mouse'; }

  function onPointerOver(event) {
    if (!isMouse(event)) return;
    var trigger = closestTrigger(event.target);
    if (state.open && (state.open.pop.contains(event.target) || state.open.trigger === trigger)) {
      if (state.closeTimer) { clearTimeout(state.closeTimer); state.closeTimer = null; }
      return;
    }
    if (!trigger) return;
    stashTitle(trigger);
    if (state.hoverTimer) clearTimeout(state.hoverTimer);
    state.hoverTimer = setTimeout(function () {
      state.hoverTimer = null;
      if (!state.open || state.open.mode !== 'pinned') open(trigger, 'hover');
    }, HOVER_OPEN_MS);
  }

  function onPointerOut(event) {
    if (!isMouse(event)) return;
    var trigger = closestTrigger(event.target);
    var to = event.relatedTarget;
    if (trigger && to && trigger.contains(to)) return;
    if (state.hoverTimer && trigger) {
      clearTimeout(state.hoverTimer);
      state.hoverTimer = null;
      if (!state.open || state.open.trigger !== trigger) restoreTitle(trigger);
    }
    if (!state.open || state.open.mode !== 'hover') return;
    if (to && (state.open.pop.contains(to) || state.open.trigger.contains(to))) return;
    if (state.closeTimer) clearTimeout(state.closeTimer);
    state.closeTimer = setTimeout(function () { state.closeTimer = null; if (state.open && state.open.mode === 'hover') close(false); }, HOVER_CLOSE_MS);
  }

  function onViewportChange() {
    if (!state.open) return;
    var r = state.open.trigger.getBoundingClientRect();
    var connected = state.doc.documentElement.contains(state.open.trigger);
    if (!connected || (r.width === 0 && r.height === 0)) { close(false); return; }
    place(state.open.pop, state.open.trigger);
  }

  function install(doc) {
    if (!doc || !doc.addEventListener || doc.__j2haInfoTip) return false;
    doc.__j2haInfoTip = true;
    state.doc = doc;
    // Phase de capture : la bulle passe avant les gestionnaires jQuery (fermeture des menus, Échap de la fenêtre modale).
    doc.addEventListener('click', onClick, true);
    doc.addEventListener('keydown', onKeydown, true);
    doc.addEventListener('focusin', onFocusIn, true);
    doc.addEventListener('pointerover', onPointerOver, true);
    doc.addEventListener('pointerout', onPointerOut, true);
    var win = doc.defaultView;
    if (win && win.addEventListener) {
      win.addEventListener('resize', onViewportChange);
      win.addEventListener('scroll', onViewportChange, true);
    }
    return true;
  }

  return {
    TRIGGERS: TRIGGERS,
    HOVER_OPEN_MS: HOVER_OPEN_MS,
    button: button,
    attach: attach,
    install: install,
    close: function () { close(false); },
    isOpen: function () { return !!state.open; },
  };
}));
