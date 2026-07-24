document.addEventListener('DOMContentLoaded', function () {
  var currentScript = document.currentScript || document.querySelector('script[data-dashboard-url]');
  var dashboardUrl = currentScript ? currentScript.dataset.dashboardUrl : '/admin';
  var dashboardPathname = new URL(dashboardUrl, window.location.origin).pathname;
  var tabs = document.querySelectorAll('.admin-sidebar__tab');

  function setActiveTab(target) {
    tabs.forEach(function (tab) {
      var isActive = tab.getAttribute('data-tab-target') === target;
      tab.classList.toggle('is-active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
  }

  function tabForPath(pathname) {
    if (!pathname) {
      return null;
    }
    if (pathname === dashboardPathname || pathname === dashboardPathname + '/') {
      return 'overview';
    }
    if (pathname.startsWith('/admin/analytics')) {
      return 'analytics';
    }
    if (pathname.startsWith('/admin/users')) {
      return 'users';
    }
    if (pathname.startsWith('/admin/content')) {
      return 'content';
    }
    if (pathname.startsWith('/admin/spotify') || pathname.startsWith('/admin/album') || pathname.startsWith('/admin/track')) {
      return 'content';
    }
    if (pathname.startsWith('/admin/artist')) {
      return 'artist';
    }
    if (pathname.startsWith('/admin/wikipedia-info')) {
      return 'wikipedia-info';
    }
    return null;
  }

  function resolveInitialTab(pathname) {
    var currentPath = pathname || window.location.pathname;
    var tab = tabForPath(currentPath);
    if (tab) {
      if (currentPath === dashboardPathname) {
        var hashTarget = window.location.hash.replace('#', '');
        return hashTarget || 'overview';
      }
      return tab;
    }
    return null;
  }

  function setActiveSidebarAction(path) {
    var actionButtons = document.querySelectorAll('[data-sidebar-action]');
    actionButtons.forEach(function (button) {
      var action = button.getAttribute('data-sidebar-action');
      var isActive = false;
      if (action === 'artist' && path.startsWith('/admin/artist')) {
        isActive = true;
      }
      if (action === 'wikipedia-info' && path.startsWith('/admin/wikipedia-info')) {
        isActive = true;
      }
      button.classList.toggle('admin-sidebar__action--active', isActive);
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
  }

  function runInlineScripts(scripts) {
    return scripts.reduce(function (promise, oldScript) {
      return promise.then(function () {
        return new Promise(function (resolve) {
          var script = document.createElement('script');
          if (oldScript.src) {
            script.src = oldScript.src;
            script.async = false;
            script.onload = resolve;
            script.onerror = resolve;
          } else {
            script.textContent = oldScript.textContent;
            resolve();
          }
          document.body.appendChild(script);
        });
      });
    }, Promise.resolve());
  }

  function loadSidebarPage(url, pushState) {
    var destinationUrl = new URL(url, window.location.origin);
    var requestedPath = destinationUrl.pathname;
    var requestedHash = destinationUrl.hash.replace('#', '');

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error('بارگیری صفحه ناموفق بود.');
        }
        return response.text();
      })
      .then(function (htmlText) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(htmlText, 'text/html');
        var newContent = doc.querySelector('.admin-content');
        if (!newContent) {
          window.location.href = url;
          return;
        }

        var currentContent = document.querySelector('.admin-content');
        if (!currentContent) {
          window.location.href = url;
          return;
        }

        currentContent.innerHTML = newContent.innerHTML;
        document.title = doc.title || document.title;
        setActiveSidebarAction(requestedPath);

        if (pushState) {
          window.history.pushState({ path: url }, '', url);
        }

        if (requestedHash) {
          setActiveTab(requestedHash);
        } else {
          setActiveTab(resolveInitialTab(requestedPath));
        }

        var newScripts = Array.from(doc.querySelectorAll('script:not([data-base-admin-script])'));
        if (newScripts.length) {
          return runInlineScripts(newScripts);
        }
      })
      .catch(function () {
        window.location.href = url;
      });
  }

  setActiveTab(resolveInitialTab());
  setActiveSidebarAction(window.location.pathname);

  window.addEventListener('popstate', function () {
    loadSidebarPage(window.location.pathname, false);
  });

  var sidebarActions = document.querySelectorAll('[data-sidebar-action]');
  sidebarActions.forEach(function (button) {
    var pageUrl = button.dataset.pageUrl;
    if (!pageUrl) {
      return;
    }
    button.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      loadSidebarPage(pageUrl, true);
    });
  });

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function (event) {
      var pageUrl = tab.dataset.pageUrl;
      if (pageUrl) {
        event.preventDefault();
        event.stopImmediatePropagation();
        loadSidebarPage(pageUrl, true);
        return;
      }

      var target = tab.getAttribute('data-tab-target');
      if (!target) {
        return;
      }
      if (window.location.pathname === dashboardPathname) {
        window.location.hash = target;
      } else {
        window.location.href = dashboardUrl + '#' + target;
      }
    });
  });
});
