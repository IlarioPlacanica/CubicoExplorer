(() => {
    'use strict';

    const body = document.body;

    const ui = {
        menuToggle: document.querySelector('.menu-toggle'),
        siteNav: document.querySelector('.site-nav'),

        revealItems: Array.from(document.querySelectorAll('.reveal')),

        indexItems: Array.from(document.querySelectorAll('.project-index-item')),
        previewContainer: document.querySelector('.project-index-preview'),
        previewImage: document.getElementById('index-preview-image'),
        previewVideo: document.getElementById('index-preview-video'),
        previewVideoSource: document.querySelector('#index-preview-video source'),
        previewCarousels: Array.from(document.querySelectorAll('.js-preview-carousel')),

        lightbox: document.getElementById('lightbox'),
        lightboxStage: document.getElementById('lightbox-stage'),
        lightboxClose: document.querySelector('.lightbox-close'),
        lightboxPrev: document.querySelector('.lightbox-nav--prev'),
        lightboxNext: document.querySelector('.lightbox-nav--next'),

        lightboxTriggers: Array.from(document.querySelectorAll('.js-open-lightbox'))
    };

    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let prefersReducedMotion = motionPreference.matches;
    motionPreference.addEventListener('change', (event) => {
        prefersReducedMotion = event.matches;
        if (prefersReducedMotion) {
            ui.lightboxStage?.querySelector('video')?.pause();
        }
    });

    const previewState = {
        type: '',
        src: ''
    };

    let lightboxItems = [];
    let lightboxIndex = -1;

    function safePlay(video) {
        if (!video || prefersReducedMotion) return;
        const playPromise = video.play();
        if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(() => {});
        }
    }

    function stopVideo(video) {
        if (!video) return;
        video.pause();
    }

    function setMenuState(isOpen) {
        if (!ui.menuToggle) return;
        body.classList.toggle('menu-open', isOpen);
        ui.menuToggle.setAttribute('aria-expanded', String(isOpen));
    }

    function initMenu() {
        if (!ui.menuToggle) return;

        ui.menuToggle.addEventListener('click', () => {
            const expanded = ui.menuToggle.getAttribute('aria-expanded') === 'true';
            setMenuState(!expanded);
        });

        if (ui.siteNav) {
            const navLinks = ui.siteNav.querySelectorAll('a');
            navLinks.forEach((link) => {
                link.addEventListener('click', () => setMenuState(false));
            });
        }
    }

    function initRevealObserver() {
        if (!ui.revealItems.length) return;

        if (prefersReducedMotion || !('IntersectionObserver' in window)) {
            ui.revealItems.forEach((item) => item.classList.add('is-visible'));
            return;
        }

        const observer = new IntersectionObserver(
            (entries, currentObserver) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;
                    entry.target.classList.add('is-visible');
                    currentObserver.unobserve(entry.target);
                });
            },
            {
                // Tall galleries may never fit enough of their height in the viewport.
                threshold: 0,
                rootMargin: '0px 0px -6% 0px'
            }
        );

        ui.revealItems.forEach((item) => observer.observe(item));
    }

    function setProjectIndexPreview(type, src) {
        if (
            !ui.previewContainer ||
            !ui.previewImage ||
            !ui.previewVideo ||
            !ui.previewVideoSource ||
            !src
        ) {
            return;
        }

        if (previewState.type === type && previewState.src === src) {
            return;
        }

        const isVideo = type === 'video';

        ui.previewContainer.classList.toggle('is-image', !isVideo);

        if (isVideo) {
            stopVideo(ui.previewVideo);
            ui.previewVideo.style.opacity = '0';

            const revealAndPlay = () => {
                ui.previewVideo.currentTime = 0;
                ui.previewVideo.style.opacity = '1';
                safePlay(ui.previewVideo);
            };

            if (ui.previewVideoSource.getAttribute('src') !== src) {
                ui.previewVideoSource.setAttribute('src', src);
                ui.previewVideo.addEventListener('loadeddata', revealAndPlay, { once: true });
                ui.previewVideo.load();
            } else {
                revealAndPlay();
            }
        } else {
            if (ui.previewImage.getAttribute('src') !== src) {
                ui.previewImage.setAttribute('src', src);
            }
            ui.previewVideo.style.opacity = '1';
            stopVideo(ui.previewVideo);
        }

        previewState.type = type;
        previewState.src = src;
    }

    function activateIndexItem(item) {
        if (!item) return;

        ui.indexItems.forEach((entry) => entry.classList.remove('is-active'));
        item.classList.add('is-active');

        setProjectIndexPreview(
            item.dataset.previewType || 'image',
            item.dataset.previewSrc || ''
        );
    }

    function initProjectIndex() {
        if (!ui.indexItems.length) return;

        const initialItem =
            ui.indexItems.find((item) => item.classList.contains('is-active')) || ui.indexItems[0];

        activateIndexItem(initialItem);

        ui.indexItems.forEach((item) => {
            const activate = () => activateIndexItem(item);
            item.addEventListener('mouseenter', activate);
            item.addEventListener('focus', activate);
            item.addEventListener('touchstart', activate, { passive: true });
        });
    }

    function initPreviewCarousels() {
        if (!ui.previewCarousels.length) return;

        ui.previewCarousels.forEach((carousel) => {
            const viewport = carousel.querySelector('.project-preview-carousel__viewport');
            const track = carousel.querySelector('.project-preview-carousel__track');
            const slides = Array.from(track?.querySelectorAll('.js-open-lightbox') || []);
            const prevButton = carousel.querySelector('.project-preview-carousel__nav--prev');
            const nextButton = carousel.querySelector('.project-preview-carousel__nav--next');
            const currentLabel = carousel.querySelector('.project-preview-carousel__status-current');
            const totalLabel = carousel.querySelector('.project-preview-carousel__status-total');

            if (!viewport || !track || !slides.length) return;

            if (totalLabel) {
                totalLabel.textContent = String(slides.length).padStart(2, '0');
            }

            const getCurrentIndex = () => {
                const scrollLeft = viewport.scrollLeft;
                let closestIndex = 0;
                let closestDistance = Number.POSITIVE_INFINITY;

                slides.forEach((slide, index) => {
                    const distance = Math.abs(slide.offsetLeft - scrollLeft);
                    if (distance < closestDistance) {
                        closestDistance = distance;
                        closestIndex = index;
                    }
                });

                return closestIndex;
            };

            const updateState = () => {
                const currentIndex = getCurrentIndex();

                if (currentLabel) {
                    currentLabel.textContent = String(currentIndex + 1).padStart(2, '0');
                }

                if (prevButton) {
                    prevButton.disabled = currentIndex === 0;
                }

                if (nextButton) {
                    nextButton.disabled = currentIndex === slides.length - 1;
                }
            };

            const scrollToSlide = (index) => {
                const clampedIndex = Math.max(0, Math.min(index, slides.length - 1));
                viewport.scrollTo({
                    left: slides[clampedIndex].offsetLeft,
                    behavior: prefersReducedMotion ? 'auto' : 'smooth'
                });
            };

            if (prevButton) {
                prevButton.addEventListener('click', () => {
                    scrollToSlide(getCurrentIndex() - 1);
                });
            }

            if (nextButton) {
                nextButton.addEventListener('click', () => {
                    scrollToSlide(getCurrentIndex() + 1);
                });
            }

            viewport.addEventListener('scroll', updateState, { passive: true });
            viewport.addEventListener('keydown', (event) => {
                if (event.key === 'ArrowLeft') {
                    event.preventDefault();
                    scrollToSlide(getCurrentIndex() - 1);
                }

                if (event.key === 'ArrowRight') {
                    event.preventDefault();
                    scrollToSlide(getCurrentIndex() + 1);
                }
            });

            window.addEventListener('resize', updateState);
            updateState();
        });
    }

    function clearLightboxStage() {
        if (!ui.lightboxStage) return;

        const activeVideo = ui.lightboxStage.querySelector('video');
        const activeIframe = ui.lightboxStage.querySelector('iframe');

        if (activeVideo) {
            activeVideo.pause();
            activeVideo.removeAttribute('src');
            activeVideo.load();
        }

        if (activeIframe) {
            activeIframe.setAttribute('src', 'about:blank');
        }

        ui.lightboxStage.innerHTML = '';
    }

    function getLightboxCaption(item) {
        return item?.caption || '';
    }

    function buildLightboxItem(trigger) {
        return {
            type: trigger.dataset.type || 'image',
            src: trigger.dataset.src || '',
            caption: trigger.dataset.caption || ''
        };
    }

    function getLightboxGroupContainer(trigger) {
        return trigger.closest('[data-lightbox-group]') || trigger.closest('.project-gallery');
    }

    function createLightboxMedia(type, src, caption) {
        let mediaNode;

        if (type === 'video') {
            mediaNode = document.createElement('video');
            mediaNode.controls = true;
            mediaNode.loop = true;
            mediaNode.playsInline = true;
            mediaNode.preload = 'metadata';
            mediaNode.src = src;

            if (!prefersReducedMotion) {
                mediaNode.autoplay = true;
            }
        } else if (type === 'tour' || type === 'viewer') {
            mediaNode = document.createElement('iframe');
            mediaNode.src = src;
            mediaNode.loading = 'lazy';
            mediaNode.allow = 'fullscreen';
            mediaNode.title = caption || (type === 'viewer' ? 'Interactive viewer' : 'Interactive tour');
        } else {
            mediaNode = document.createElement('img');
            mediaNode.src = src;
            mediaNode.alt = caption || 'Portfolio media';
            mediaNode.loading = 'eager';
        }

        return mediaNode;
    }

    function updateLightboxNav() {
        if (!ui.lightboxPrev || !ui.lightboxNext) return;

        const showNav = lightboxItems.length > 1;
        ui.lightboxPrev.classList.toggle('is-hidden', !showNav);
        ui.lightboxNext.classList.toggle('is-hidden', !showNav);
    }

    function renderLightboxItem(index) {
        if (!ui.lightboxStage) return;
        if (!lightboxItems.length) return;
        if (index < 0 || index >= lightboxItems.length) return;

        lightboxIndex = index;
        clearLightboxStage();

        const item = lightboxItems[lightboxIndex];
        const caption = getLightboxCaption(item);
        const mediaNode = createLightboxMedia(item.type, item.src, caption);

        ui.lightboxStage.appendChild(mediaNode);

        if (mediaNode.tagName === 'VIDEO') {
            safePlay(mediaNode);
        }

        updateLightboxNav();
    }

    function openLightboxGroup(items, startIndex = 0) {
        if (!ui.lightbox || !items.length) return;

        lightboxItems = items.filter((item) => item.src);

        if (!lightboxItems.length) return;

        renderLightboxItem(startIndex);

        ui.lightbox.classList.add('is-open');
        ui.lightbox.setAttribute('aria-hidden', 'false');
        body.classList.add('lightbox-open');
    }

    function openLightbox(type, src, caption = '') {
        openLightboxGroup([{ type, src, caption }], 0);
    }

    function showPreviousLightboxItem() {
        if (lightboxItems.length <= 1) return;
        const nextIndex = (lightboxIndex - 1 + lightboxItems.length) % lightboxItems.length;
        renderLightboxItem(nextIndex);
    }

    function showNextLightboxItem() {
        if (lightboxItems.length <= 1) return;
        const nextIndex = (lightboxIndex + 1) % lightboxItems.length;
        renderLightboxItem(nextIndex);
    }

    function closeLightbox() {
        if (!ui.lightbox) return;

        clearLightboxStage();
        ui.lightbox.classList.remove('is-open');
        ui.lightbox.setAttribute('aria-hidden', 'true');

        body.classList.remove('lightbox-open');

        lightboxItems = [];
        lightboxIndex = -1;
    }

    function buildGalleryItems(trigger) {
        const gallery = getLightboxGroupContainer(trigger);

        if (!gallery) {
            return [buildLightboxItem(trigger)];
        }

        const galleryTriggers = Array.from(gallery.querySelectorAll('.js-open-lightbox'));

        return galleryTriggers.map(buildLightboxItem);
    }

    function initLightbox() {
        if (!ui.lightboxTriggers.length) return;

        ui.lightboxTriggers.forEach((trigger) => {
            trigger.addEventListener('click', (event) => {
                event.preventDefault();

                const gallery = getLightboxGroupContainer(trigger);
                const items = buildGalleryItems(trigger);

                if (gallery) {
                    const galleryTriggers = Array.from(gallery.querySelectorAll('.js-open-lightbox'));
                    const startIndex = galleryTriggers.indexOf(trigger);
                    openLightboxGroup(items, startIndex >= 0 ? startIndex : 0);
                    return;
                }

                openLightbox(
                    trigger.dataset.type || 'image',
                    trigger.dataset.src || '',
                    trigger.dataset.caption || ''
                );
            });

            if (trigger.tagName !== 'BUTTON' && trigger.tagName !== 'A') {
                trigger.addEventListener('keydown', (event) => {
                    if (event.key !== 'Enter' && event.key !== ' ') return;
                    event.preventDefault();
                    trigger.click();
                });
            }
        });

        if (ui.lightboxClose) {
            ui.lightboxClose.addEventListener('click', closeLightbox);
        }

        if (ui.lightboxPrev) {
            ui.lightboxPrev.addEventListener('click', (event) => {
                event.stopPropagation();
                showPreviousLightboxItem();
            });
        }

        if (ui.lightboxNext) {
            ui.lightboxNext.addEventListener('click', (event) => {
                event.stopPropagation();
                showNextLightboxItem();
            });
        }

        if (ui.lightbox) {
            ui.lightbox.addEventListener('click', (event) => {
                if (event.target === ui.lightbox) {
                    closeLightbox();
                }
            });
        }
    }

    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeLightbox();
                setMenuState(false);
                return;
            }

            if (!ui.lightbox || !ui.lightbox.classList.contains('is-open')) return;

            if (event.key === 'ArrowLeft') {
                showPreviousLightboxItem();
            }

            if (event.key === 'ArrowRight') {
                showNextLightboxItem();
            }
        });
    }

    function init() {
        initMenu();
        initRevealObserver();
        initProjectIndex();
        initPreviewCarousels();
        initLightbox();
        initKeyboardShortcuts();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
