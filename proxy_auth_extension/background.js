
console.log('Proxy6 Auth Extension: Starting');

var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "http",
            host: "196.16.220.52",
            port: parseInt("8000")
        },
        bypassList: ["localhost", "127.0.0.1", "::1"]
    }
};

// Настройка прокси с обработкой ошибок
chrome.proxy.settings.set({value: config, scope: "regular"}, function() {
    if (chrome.runtime.lastError) {
        console.error('Proxy6 Auth Extension: Error setting proxy:', chrome.runtime.lastError);
    } else {
        console.log('Proxy6 Auth Extension: Proxy configured successfully');
    }
});

// Обработчик авторизации с логированием
function callbackFn(details) {
    console.log('Proxy6 Auth Extension: Auth request for', details.url);
    return {
        authCredentials: {
            username: "GALsB4",
            password: "6UwJ3b"
        }
    };
}

// Подписка на события авторизации
chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {urls: ["<all_urls>"]},
    ['blocking']
);

console.log('Proxy6 Auth Extension: Ready');
