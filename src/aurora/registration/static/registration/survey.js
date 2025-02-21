(function ($) {
    var queryParams = window.location.search.substring(1).split('&').reduce(function (q, query) {
        var chunks = query.split('=');
        var key = chunks[0];
        var value = decodeURIComponent(chunks[1]);
        value = isNaN(Number(value)) ? value : Number(value);
        return (q[key] = value, q);
    }, {});
    var get_session = function () {
        return queryParams['s'];
    }
    $(function () {
        // we need this HACK to manage the stupid cache system in front of the app
        const pk = $("meta[name=\"RegId\"]").attr("content");
        const lang = $("meta[name=\"Language\"]").attr("content");
        const sessionUrl = get_session();
        var parts = location.href.split("/");
        console.log(lang);
        $.get("/api/registration/" + pk + "/" + lang + "/version/?" + Math.random(), function (data) {
            const version = parseInt(parts[parts.length - 2]);
            if (version !== data.version) {
                console.log("version mismatch: redirect", data.url)
                location.href = data.url;
            } else if (data.auth && (data.session_id !== sessionUrl)) {
                console.log("session_id mismatch: redirect", data.url)
                location.href = data.url;
            } else if (!data.auth && sessionUrl) {
                console.log("session_id tampered with: redirect", data.url)
                location.href = data.url;
            } else {
                console.log("version matches", data.url)
            }
        });
    });
})($);
