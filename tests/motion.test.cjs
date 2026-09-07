const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function run(reduced, supported = true) {
    const element = () => {
        const classes = new Set(), styles = new Map();
        return {
            classes, styles, children: [],
            classList: { add(v) { classes.add(v); }, remove(v) { classes.delete(v); }, contains(v) { return classes.has(v); }, toggle(v, on) { if (on) classes.add(v); else classes.delete(v); } },
            style: { setProperty(k, v) { styles.set(k, v); }, removeProperty(k) { styles.delete(k); } }
        };
    };
    const body = element(), hero = element(), copy = element(), workflow = element();
    const feature = element(), featureVideo = element();
    feature.querySelector = () => featureVideo;
    feature.getBoundingClientRect = () => ({top: 500, height: 700});
    const steps = Array.from({length: 3}, element), row = element();
    row.children = [element(), element()];
    row.children[0].children = [element(), element(), element()];
    steps.forEach(step => { step.children = [element(), element(), element()]; });
    hero.querySelector = () => copy;
    let heroTop = 0;
    hero.getBoundingClientRect = () => ({top: heroTop, height: 1000});
    workflow.getBoundingClientRect = () => ({top: 400, height: 300});
    workflow.querySelectorAll = () => steps;
    workflow.closest = () => element();
    workflow.previousElementSibling = element();
    const video = {paused: true, autoplay: true, play() {this.paused = false; return Promise.resolve();}, pause() {this.paused = true;}};
    const observers = [], events = {}, preference = {matches: reduced, addEventListener(_, cb) {this.change = cb;}};
    let frameCallback, frameCount = 0, mutation;
    function Observer(cb) { this.callback = cb; this.observe = () => {}; observers.push(this); }
    const document = {body, hidden: false, querySelector(s) { return s.includes('project-split') ? feature : s.includes('project-work-1') ? hero : workflow; }, querySelectorAll(s) { return s.startsWith('main') ? [video] : [row]; }, addEventListener(n, cb) { events[n] = cb; }};
    const window = {innerHeight: 1000, matchMedia: (s) => s.includes('min-width') ? {matches: true} : preference, addEventListener(n, cb, options) {events[n] = cb; assert.equal(options.passive, true);}};
    if (supported) window.IntersectionObserver = Observer;
    vm.runInNewContext(fs.readFileSync('motion.js', 'utf8'), {
        document, window, IntersectionObserver: Observer,
        MutationObserver: function(cb) { mutation = cb; this.observe = () => {}; },
        requestAnimationFrame(cb) { frameCallback = cb; return ++frameCount; }, cancelAnimationFrame() {frameCallback = null;}
    });
    assert.equal(video.autoplay, false);
    assert.equal(video.paused, true);
    assert.equal(body.classes.has('motion-enabled'), !reduced);
    assert.equal(body.classes.has('reveal-enabled'), supported);
    assert.equal(row.children[1].styles.get('--reveal-delay'), '450ms');
    assert.equal(row.children[0].children[2].styles.get('--part-delay'), '300ms');
    assert.equal(row.classes.has('motion-reveal-group'), true);
    if (!supported) return;
    observers[1].callback([{target: video, isIntersecting: true}]);
    assert.equal(video.paused, reduced);
    if (reduced) { assert.equal(frameCount, 0); return; }
    events.scroll(); events.scroll();
    assert.equal(frameCount, 1, 'Scroll events must share one animation frame');
    heroTop = -500;
    frameCallback();
    assert.equal(hero.styles.get('--hero-drift'), '50px');
    assert.equal(hero.styles.get('--hero-copy-drift'), '-40px');
    assert.equal(hero.styles.get('--hero-scroll-scale'), '1.025');
    assert.ok(Math.abs(Number(featureVideo.styles.get('--feature-scale')) - 0.95) < 0.0001);
    assert.equal(featureVideo.styles.get('--feature-radius'), '18px');
    assert.ok(Number(hero.styles.get('--hero-copy-opacity')) < 1);
    body.classList.add('lightbox-open'); mutation(); assert.equal(video.paused, true);
    body.classList.remove('lightbox-open'); mutation(); assert.equal(video.paused, false);
    document.hidden = true; events.visibilitychange(); assert.equal(video.paused, true);
    document.hidden = false; events.visibilitychange(); assert.equal(video.paused, false);
    observers[1].callback([{target: video, isIntersecting: false}]); assert.equal(video.paused, true);
    preference.matches = true; preference.change();
    assert.equal(body.classes.has('motion-enabled'), false);
    assert.equal(hero.styles.size, 0);
    assert.equal(featureVideo.styles.size, 0);
    assert.equal(video.paused, true);
}
run(false); run(true); run(false, false);
// A shared row trigger keeps media delays relative to the text, even on fast scroll.
{
    const source = fs.readFileSync('script.js', 'utf8');
    const code = source.slice(source.indexOf('    function initRevealObserver()'), source.indexOf('    function setProjectIndexPreview'));
    let callback, options;
    const observed = [], revealed = [];
    const group = {classList: {contains: () => true}, querySelectorAll: () => items};
    const items = [0, 1].map(index => ({closest: () => group, classList: {add: () => revealed.push(index)}}));
    const observer = {observe: target => observed.push(target), unobserve: () => {}};
    function IntersectionObserver(cb, opts) { callback = cb; options = opts; return observer; }
    vm.runInNewContext(code + 'initRevealObserver();', {ui: {revealItems: items}, prefersReducedMotion: false, window: {IntersectionObserver}, IntersectionObserver});
    assert.equal(observed.length, 1);
    assert.equal(options.threshold, 0);
    callback([{target: group, isIntersecting: true}], observer);
    assert.deepEqual(revealed, [0, 1]);
}
console.log('Passed: stagger, parallax bounds, one frame per scroll batch, video visibility/lightbox/tab pause, reduced motion and observer fallback.');
