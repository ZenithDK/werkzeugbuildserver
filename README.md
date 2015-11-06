# werkzeugbuildserver

## Running locally

The first time you run buildserver.py you need to supply some default configuration values.
I have made the following assumptions:
* python is in your path
* This repository has been cloned to C:\werkzeugbuildserver
* You checkout all you SVN repos to C:\Projects
```
> python C:\werkzeugbuildserver\buildserver.py --base C:\Projects --key mySecretKey --save
```

You can now initiate a build from where-ever in your Project folders:
```
> python C:\werkzeugbuildserver\buildclient.py --key mySecretKey --save
```

Since you have now executed both the server and the client with the --save argument, you
can exectute both scripts without any arguments in the future. The default hostname and key
has been saved.

If you want to build a different target (default is "all"), like xide, you supply the -t parameter.

```
> python C:\werkzeugbuildserver\buildclient.py -t xide
```

Lastly, you could also create some Vim shortcuts (which is actually the whole purpose of this project) and add them to your .vimrc:

```VimL
map <Leader>c :!buildclient.py<CR>
map <Leader>r :!buildclient.py -t xide<CR>
```

## Defining exceptions

Some projects have some exceptions with regards to how they're built.

One example might the the "application" folder, perhaps a project isn't built with the default folder but a different one instead.

To manage this, you can put an "exceptions.ini" file to your "base" folder.

Example (C:\Projects\exceptions.ini):
```INI
[P0096_platform]
application = P0124_everest
```
