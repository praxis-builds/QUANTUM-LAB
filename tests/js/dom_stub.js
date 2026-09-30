"use strict";
// A deliberately small DOM stand-in: enough for the dashboard scripts to run their real
// rendering and event code under Node. It is not a browser and does no layout or painting.
class ClassList {
  constructor(owner) { this.owner = owner; this.set = new Set(); }
  add(...names) { names.forEach((n) => this.set.add(n)); }
  remove(...names) { names.forEach((n) => this.set.delete(n)); }
  toggle(name, force) { const on = force === undefined ? !this.set.has(name) : Boolean(force); if (on) this.set.add(name); else this.set.delete(name); return on; }
  contains(name) { return this.set.has(name); }
  toString() { return [...this.set].join(" "); }
}
class Node {
  constructor(tag, namespace) {
    this.tagName = String(tag).toUpperCase(); this.localName = tag; this.namespaceURI = namespace || null;
    this.children = []; this.parentNode = null; this.attributes = {}; this.listeners = {};
    this.classList = new ClassList(this); this.style = {}; this.ownText = ""; this.hidden = false;
    this.value = ""; this.disabled = false; this.dataset = {};
  }
  get className() { return this.classList.toString(); }
  set className(value) { this.classList = new ClassList(this); String(value).split(/\s+/).filter(Boolean).forEach((c) => this.classList.add(c)); }
  setAttribute(name, value) { this.attributes[name] = String(value); if (name === "class") this.className = value; if (name === "id") this.id = String(value); }
  getAttribute(name) { return name === "class" ? this.className : (name in this.attributes ? this.attributes[name] : null); }
  removeAttribute(name) { delete this.attributes[name]; }
  append(...nodes) { for (const item of nodes) { const node = typeof item === "string" ? textNode(item) : item; if (node.parentNode) node.remove(); node.parentNode = this; this.children.push(node); } }
  appendChild(node) { this.append(node); return node; }
  replaceChildren(...nodes) { for (const child of this.children) child.parentNode = null; this.children = []; this.append(...nodes); }
  remove() { if (this.parentNode) { this.parentNode.children = this.parentNode.children.filter((c) => c !== this); this.parentNode = null; } }
  get textContent() { return this.ownText + this.children.map((c) => c.textContent).join(""); }
  set textContent(value) { this.ownText = String(value); this.replaceChildren(); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  removeEventListener(type, handler) { this.listeners[type] = (this.listeners[type] || []).filter((h) => h !== handler); }
  dispatch(type, extra = {}) {
    const event = {type, target: this, currentTarget: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, stopPropagation() {}, ...extra};
    for (const handler of this.listeners[type] || []) handler.call(this, event);
    return event;
  }
  click() { if (!this.disabled) this.dispatch("click"); }
  focus() {}
  setPointerCapture() {}
  releasePointerCapture() {}
  getBoundingClientRect() { return {left: 0, top: 0, width: 600, height: 300}; }
  reportValidity() { return true; }
  querySelectorAll() { return []; }
  getContext() { return null; }
  descendants() { return this.children.flatMap((c) => [c, ...c.descendants()]); }
  find(predicate) { return this.descendants().find(predicate) || null; }
  findAll(predicate) { return this.descendants().filter(predicate); }
}
function textNode(text) { const node = new Node("#text"); node.ownText = String(text); return node; }

function createEnvironment() {
  const registry = new Map();
  const documentElement = new Node("html");
  const document = {
    documentElement,
    listeners: {},
    getElementById(id) { if (!registry.has(id)) { const node = new Node("div"); node.id = id; registry.set(id, node); } return registry.get(id); },
    createElement(tag) { return new Node(tag); },
    createElementNS(namespace, tag) { return new Node(tag, namespace); },
    createTextNode: textNode,
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    dispatchEvent(event) { for (const handler of this.listeners[event.type] || []) handler(event); return true; }
  };
  const getComputedStyle = () => ({getPropertyValue: () => ""});
  return {document, registry, getComputedStyle};
}
module.exports = {Node, createEnvironment};
