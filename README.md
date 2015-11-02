# csrbuildshortcuts

build_current.sh and run_current.sh are shellscripts I've added to my path and then created Vim shortcuts for:
```
map <Leader>c :silent !build_current.sh<CR>
map <Leader>r :silent !run_current.sh<CR>
```

build.py is a script I execute on the Windoze machine that watches the files touched by the shellscripts.
