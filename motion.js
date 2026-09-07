(() => {
    'use strict';

    const body = document.body;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const canObserve = 'IntersectionObserver' in window;
    const hero = document.querySelector('.project-work-1 .project-hero');
    const heroCopy = hero?.querySelector('.project-hero-copy');
    const workflow = document.querySelector('.project-workflow-grid');
    const steps = Array.from(workflow?.querySelectorAll('article') || []);
    const videos = Array.from(document.querySelectorAll('main video[muted][loop]'));
    const visibleVideos = new Set();
    let heroVisible = true;
    let workflowVisible = true;
    let frame = 0;

    // Reveal the copy and media separately, without hiding a whole tall section.
    document.querySelectorAll('.project-gallery-feature, .project-split').forEach((row) => {
        row.classList.remove('reveal');
        Array.from(row.children).forEach((child, index) => {
            child.classList.add('reveal');
            child.style.setProperty('--reveal-delay', index ? '150ms' : '0ms');
        });
    });
    if (workflow) {
        workflow.closest('.project-workflow')?.classList.remove('reveal');
        workflow.previousElementSibling?.classList.add('reveal');
        steps.forEach((step, index) => {
            step.classList.add('reveal');
            step.style.setProperty('--reveal-delay', `${index * 100}ms`);
        });
    }
    heroCopy?.classList.remove('reveal');

    const clamp = (value) => Math.max(0, Math.min(1, value));

    function renderScroll() {
        frame = 0;
        if (preference.matches || document.hidden) return;
        // Read layout first, then write only compositor-friendly transforms/opacity.
        const heroRect = heroVisible ? hero?.getBoundingClientRect() : null;
        const workflowRect = workflowVisible ? workflow?.getBoundingClientRect() : null;
        if (heroRect) {
            const progress = clamp(-heroRect.top / Math.max(heroRect.height, 1));
            hero.style.setProperty('--hero-drift', `${Math.min(heroRect.height * 0.07, 65) * progress}px`);
            hero.style.setProperty('--hero-copy-drift', `${-32 * progress}px`);
            hero.style.setProperty('--hero-copy-opacity', String(1 - clamp((progress - 0.12) / 0.78)));
        }
        if (workflowRect) {
            const progress = clamp((window.innerHeight * 0.68 - workflowRect.top) / Math.max(workflowRect.height, 1));
            const active = Math.min(steps.length - 1, Math.floor(progress * steps.length));
            steps.forEach((step, index) => {
                step.classList.toggle('is-current', active === index);
                step.style.setProperty('--step-progress', String(clamp(progress * steps.length - index)));
            });
        }
    }

    function scheduleScroll() {
        if (!frame && !preference.matches && !document.hidden && (heroVisible || workflowVisible)) {
            frame = requestAnimationFrame(renderScroll);
        }
    }

    function syncVideos() {
        videos.forEach((video) => {
            const shouldPlay = !preference.matches && !document.hidden &&
                !body.classList.contains('lightbox-open') && visibleVideos.has(video);
            if (shouldPlay) {
                if (video.paused) video.play()?.catch(() => {});
            } else {
                video.pause();
            }
        });
    }

    function syncPreference() {
        body.classList.toggle('motion-enabled', !preference.matches);
        if (preference.matches) {
            if (frame) cancelAnimationFrame(frame);
            frame = 0;
            ['--hero-drift', '--hero-copy-drift', '--hero-copy-opacity'].forEach((name) => hero?.style.removeProperty(name));
            steps.forEach((step) => {
                step.classList.remove('is-current');
                step.style.removeProperty('--step-progress');
            });
        }
        syncVideos();
        scheduleScroll();
    }

    if (canObserve) {
        const sceneObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.target === hero) heroVisible = entry.isIntersecting;
                if (entry.target === workflow) workflowVisible = entry.isIntersecting;
            });
            scheduleScroll();
        }, { threshold: 0 });
        if (hero) sceneObserver.observe(hero);
        if (workflow) sceneObserver.observe(workflow);

        const videoObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) visibleVideos.add(entry.target);
                else visibleVideos.delete(entry.target);
            });
            syncVideos();
        }, { threshold: 0 });
        videos.forEach((video) => videoObserver.observe(video));
    }
    videos.forEach((video) => {
        video.autoplay = false;
        video.pause();
    });
    new MutationObserver(syncVideos).observe(body, { attributes: true, attributeFilter: ['class'] });
    window.addEventListener('scroll', scheduleScroll, { passive: true });
    window.addEventListener('resize', scheduleScroll, { passive: true });
    document.addEventListener('visibilitychange', () => {
        syncVideos();
        scheduleScroll();
    });
    preference.addEventListener('change', syncPreference);
    syncPreference();
    // Without JavaScript or IntersectionObserver, content remains visible.
    body.classList.toggle('reveal-enabled', canObserve);
})();
