fcrawl+
=======

### What is fcrawl+?
It's fcrawl plus:

  - monster list
  - status line
  - improved interface 
    * HUD
    * warp
    * force_more
    * alchemy
    * [beta] xv
    * notes
    * encoding on Windows
    * py2+py3 support
  - role removal
  - death messages
  - scoring
  - rune lock
  - V:5
  - Slime
  - Surfac
  - changed running
  - hydra slayer
  - flying
  - mummies
  - rumors
  - optional HARD mode
  - pizza
  - vaults and zoos
  - many new monsters
  - new layouts and larger maps!

### New monsters?!
Yes. These:

  - ogre
  - ice beast
  - orb hound
  - vault guard
  - frog
  - torpedo
  - wyvern
  - vampire
  - bear
  - mosquito
  - oklob
  - skeleton
  - jump spider
  - shining eye
  - orb snake
  - acid blob
  - sentinel
  - azure ooze
  - Rupert
  - royal jelly

### Install and run
To install, get the file `fcrawl.py` from somewhere.
To play, execute it like this: `python fcrawl.py`.

For a list of supported command line options, run `python fcrawl.py -h`.
For a drastically less cool list of said options, check the next section.

### Command line options
Note that some of these options can change gameplay *significantly* --
in particular, `-w` activates wizard mode,
while `-x` enables HARD mode
and `-m` turns you into a mummy.

Others are simply UX streamlining:
with `-n` (or `-u`) you can predefine your player name,
`-q` suppresses the interface help displayed upon game start.

### Ingame commands
You could just have started a game or pressed `?` ingame, but here we go:
```
 [hjklyubn] move  [s.] wait  [<>] stairs  [gG] warp
 [HJKLYUBN] run   [1234560] quaff potion  [?!] help
 [!] show hints   [ ] read more messages  [:_] chat
```

Some hints are quite useful, especially if you are unfamiliar with `fcrawl`.

### How do I interact with doors?
Open doors by moving into them. You cannot close doors.

### Hall of `f`ame
A file `my-fcrawl-games.txt` is created where you invoke fcrawl.
It contains the fate of your noteworthy characters once they die of old age
or (highly unlikely) from less natural causes.

### Who should I thank for this masterful masterpiece?

- **Them** for Dungeon Crawl: Stone Soup, a roguelike adventure through
  dungeons filled with dangerous monsters in a quest to find the
  mystifyingly fabulous ~~choko~~ Orb of Zot
- Us, the `fcrawl` developers, for meticulously building fcrawl according
  to its extensive development directions provided with this Readme
- Guido, the former BDFL of Python, for willing and guiding a great language
  into the place it has today, allowing you to run `fcrawl` on your machine
- **Yourself** for discovering the pinnacle of roguelike games, at least
  but most likely not limited to those starting with lowercase `f`
- And lastly, half and Scatha for Sil, 
  ```
  A game of adventure set
      in the first age of Middle-earth,
          when the world still rang with elven song
              and gleamed with dwarven mail.
  
  Walk the dark halls of Angband.
      Slay creatures black and fell.
          Wrest a shining Silmaril from Morgoth’s iron crown.
   ```

### I'm just here to figure out why fcrawl is called fcrawl. So why is fcrawl called fcrawl????
Many have tried to figure this out. Even more have failed. Theories galore.

```
<fcrawl> it's a little known fact that fcrawl is named after me, fcrawl
```

