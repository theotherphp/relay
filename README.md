## Relay

This is a computerized lap counter system intended for walkathons like the American Cancer Society [Relay for Life&reg;](https://secure.acsevents.org/site/SPageServer?pagename=relay_learn). I built it as a volunteer to use at my local event in Northern California.

### How does it work?

There are three main pieces of code:

1. RFID reader. I bought [ThingMagic-based RFID modules](https://www.sparkfun.com/products/14066) from Sparkfun, powered them with [Arduino boards](https://www.sparkfun.com/products/13975), and programmed the serial connection using Per Gotthard’s handy [python-to-ThingMagic library](https://github.com/gotthardp/python-mercuryapi) running on a Raspberry Pi Zero W.

2. Server. To get leaderboard functionality, I used [RethinkDB](rethinkdb.com) in python, and wrote a little web sockets server using [Tornado](tornadoweb.org). I run the server on a Raspberry Pi 3 but any python environment should work.

3. TV UI. To get a TV display of the leaderboard, I used Spencer P’s [Lap-Counter-Viewer](),  which was designed for this application, and hacked on it a bit. I run the browser client on a Raspberry Pi 3, but any browser environment should work.

### How are laps tracked?

1. I’m using commonly-available [ISO 18000-6C RFID tags](https://www.sparkfun.com/products/14151), which have adhesive backing to stick to [race bibs](https://www.amazon.com/Clinch-Star-Running-Numbers-Marathon/dp/B075RDTTLT/). Participants at the walkathon use safety pins to attach the race bib to their shirt.
2. I mounted Sparkfun’s [RFID antenna](https://www.sparkfun.com/products/14131) to a tripod. It reads tags from about 15 feet away, at full read power, with clear line of sight. Tag orientation on the bib matters!

### How do you manage it?
1. I start and stop the python apps (relay_app, relay_rfid) using a terminal emulator on an iPad. Any ssh client should work.
2. The Server component mentioned above also serves some RESTful web pages for adding teams, and associating RFID tags with teams. Another reason to have the iPad on hand.

### Caveats
1. RethinkDB is really cool, but there's no official distribution for ARM/Raspbian and building it takes a bit of effort.
2. Why not Flask instead of Tornado? I wanted to use websockets, and the rest of the coroutine gunk came along for the ride. Maybe there's an easier way.