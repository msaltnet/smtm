# Jupyter Notebook
We recommend jupyter notebook to run and config dynamically.

[Jupyter Notebook](https://jupyter.org/)

How to run jupyter notebook in remote server by ssh
```
ipykernel kernel --debug > klog.file 2>&1 
nohup jupyter notebook > /dev/null &
```

How to convert `.ipynb` to `.py`:
```
jupyter nbconvert --to script [YOUR_NOTEBOOK].ipynb
```

How to run with https
```
jupyter notebook --certfile=mycert.pem --keyfile mykey.key --no-browser
```
