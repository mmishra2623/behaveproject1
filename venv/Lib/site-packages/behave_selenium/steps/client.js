/* INSERT THIS SCRIPT IN THE TOPMOST PART OF YOUR PAGE HEAD */

if (typeof(window.top.__behave_selenium) != "object") {
    window.top.__behave_selenium = {
        '_fn_logger': window.top.console.log.bind(window.top.console),
        'log': [],
        'dom': null,
        '_fn_getDOM': function() {
            var newdom = document.documentElement.innerHTML;
            if (newdom != window.top.__behave_selenium['dom']) {
                window.top.__behave_selenium['dom'] = newdom;
                return newdom;
            } else {
                return null;
            }
        }
    }
        
}

/* Hook window.console.log */
window.console.log = function (msg) {
    window.top.__behave_selenium['log'].push(msg);
    return window.top.__behave_selenium['_fn_logger'](msg);
}

var elem = document.getElementById("behave-selenium-client");
elem.parentNode.removeChild(elem);
