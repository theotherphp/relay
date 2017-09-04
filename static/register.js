/*
 * register.js
 *
 * Registers walkers at the volunteer desk
 */

var socket;
var vue;

function initialize() {
    vue = new Vue({
        el: "#register_app",
        data: {
            registered_online: true,
            teams: [
                {
                    "name": "Sixers",
                    "captain": "Julius Erving",
                    "id": 0
                }
            ],
            walkers: [
                {
                    "name": "Phil Peterson",
                    "id": 0
                }
            ],
            tag: "",
            selected_team_id: 0,
            selected_walker_id: 0,
            new_walker_name: ""
        },
        delimiters: ["[[", "]]"]  // disambiguate from Tornado templates
    });
    ws_connect();
    document.getElementById("register_app").style.display = "initial";
}

function ws_connect() {
    hostname = (navigator.platform == "MacIntel") ? "10.0.1.20" : "relay.local";
    url = "ws://" + hostname + ":8888/inventory_ws";
    socket = new WebSocket(url);
    socket.onopen = e => console.log(e);
    socket.onclose = e => console.log(e);
    socket.onerror = e => console.log(e);
    socket.onmessage = ws_onmessage;
}

function ws_onmessage(message) {
    vue.tag = message.data;
}

