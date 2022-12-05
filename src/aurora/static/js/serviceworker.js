const version = 1;

let staticName = `staticCache-${version}`;
let dynamicName = `dynamicCache`;
let imageName = `imageCache-${version}`;

let assets = [
    "/",
    "/registrations/",
    "/serviceworker.js",
    "/api/project/",

    "/static/registration/survey.min.js",
    "/static/admin/js/vendor/jquery/jquery.js",

    "https://code.jquery.com/jquery-3.6.0.min.js",
    "/i18n/en-us/",
    "/static/admin/debug.css",
    "/static/staff-toolbar.css",
    "/static/base.css",
    "https://unpkg.com/tailwindcss@1.9.6/dist/tailwind.min.css",
    "/static/i18n/i18n.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/js-cookie/3.0.1/js.cookie.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/css/select2.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/select2/4.1.0-beta.1/js/select2.min.js",
    "/static/smart.js",
    "/static/select2/ajax_select.js",
    "/static/i18n/i18n_edit.js",
    "/static/page.min.js",
    "/static/hope1.webp",
    "/static/edit.min.js",
    "/static/registration/auth.js",
    "https://browser.sentry-cdn.com/5.30.0/bundle.min.js"
];

let imageAssets = [];


const synchronizeRegistrationVersion = () => {
    const url = "http://localhost:8000/en-us/";

    fetch(`${url}get_pwa_enabled/`)
    .then(fetchResponse => fetchResponse.json())
    .then(response => {
        const searchedUrl = `/en-us/register/${response.slug}/${response.version}/`;

        caches.open("staticCache-1").then(cache => {
            cache.keys().then(keys => {
                keys.forEach(key => {
                    if (key.url.match(/\/register\//)) {
                        cache.delete(key).then(() => `Key ${key} deleted from cache`)
                    }
                })
            }).then(() => {
                cache.add(searchedUrl)
                .then(() => console.log("Version of pwa-enabled registration synchronized"))
            })
        })
    })
    .catch(err => console.log(`Sorry, we couldn't synchronize data because of this error: ${err}`));
};

const handleFetchResponse = (fetchResponse, request) => {
  let type = fetchResponse.headers.get('content-type');

  if (type && type.match(/^image\//i)) {
    console.log(`SAVE ${request.url} in ${imageName}`);

    return caches.open(imageName).then((cache) => {
      cache.put(request, fetchResponse.clone());
      return fetchResponse;
    });
  } else {
    console.log(`SAVE ${request.url} in ${dynamicName}`);

    return caches.open(dynamicName).then((cache) => {
      cache.put(request, fetchResponse.clone());
      return fetchResponse;
    });
  }
};


self.addEventListener("install", event => {
  console.log(`Version ${version} installed - caching started`);

  event.waitUntil(
    caches.open(staticName)
    .then(cache => {
        cache.addAll(assets).then(
            () => {
              console.log(`${staticName} has been updated.`);
            },
            err => {
              console.warn(`Failed to update ${staticName}, ${err}`)
            }
        )
    })
    .then(() => {
       caches.open(imageName).then(cache => {
           cache.addAll(imageAssets).then(
            () => {
              console.log(`${imageName} has been updated.`);
            },
            err => {
              console.warn(`failed to update ${staticName}.`);
            }
          );
       });
    })
    .then(() => synchronizeRegistrationVersion())
  );
});


self.addEventListener("activate", event => {
   console.log("Activated - previous cache will be cleared");

   event.waitUntil(
     caches.keys().then(keys => {
        return Promise.all(
            keys.filter(key => key !== staticName && key !== imageName).map(key => caches.delete(key))
        );
     })
   );
});


self.addEventListener("fetch", event => {
    console.log(`Fetching request for: ${event.request.url}`);

    if (!event.request.url.endsWith("/")) {
        event.request.url = event.request.url + "/";
    }

    event.respondWith(
        fetch(event.request).catch(() => {
            caches.match(event.request).then(cacheResponse => {
                return cacheResponse ||
                    Promise.resolve().then(() => {
                        let options = {
                            mode: event.request.mode,
                            cache: "no-cache"
                        };

                        if (!event.request.url.startsWith(location.origin)) {
                            options.mode = "cors";
                            options.credentials = "omit";
                        }

                        return fetch(event.request.url, options).then(
                            fetchResponse => {
                                if (fetchResponse.ok) {
                                    return handleFetchResponse(fetchResponse, event.request);
                                }

                                if (fetchResponse.status === 404) {
                                    if (
                                        event.request.url.match(/\.jpg$/i) ||
                                        event.request.url.match(/\.png$/i)
                                    ) {
                                        return caches.open(imageName).then((cache) => {
                                            return cache.match('/img/distracted-boyfriend.jpg');
                                        });
                                    } else {
                                        return caches.open(staticName).then(cache => {
                                            return cache.match("/offline/")
                                        })
                                    }
                                }
                            },
                            err => {
                                return caches.open(staticName).then(cache => {
                                    return cache.match("/offline/")
                                })
                            }
                        );
                    });

            })
        })
    );
});
