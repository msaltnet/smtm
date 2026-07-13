# 개발팁

커밋을 생성하기 전에 아래 명령어를 사용하여 Jupyter notebook의 출력을 삭제하세요.

```bash
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```

원격 터미널에서 프로그램 실행 후 연결을 종료하더라도 프로그램이 종료되지 않도록 하기 위해서 `nohup`을 사용하는 방법이 있습니다. 표준 출력과 에러를 별도의 파일에 저장하며 백그라운드로 실행하기 위해서는 다음과 같이 실행하면 됩니다.

```bash
nohup python -m smtm --token <telegram_token> --chatid <chat_id> > nohup.out 2> nohup.err < /dev/null &
```

# Tips

clear jupyter notebook output before make commit

```bash
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```

For keeping smtm program process after terminating ssh connection, using `nohup` is recommended as below. Standard, error ouput is redirected to specific files.

```bash
nohup python -m smtm --token <telegram_token> --chatid <chat_id> > nohup.out 2> nohup.err < /dev/null &
```
