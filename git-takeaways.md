## Gitlab Takeaways: Git Basics for the Team

### 1. **Skapa och Byta Branch**

Innan du börjar arbeta på en ny funktion eller fixa en bugg, se till att du är i `dev`-branchen:

```sh
git checkout dev
```

För att börja arbeta på en ny funktion eller fixa en bugg, skapa en ny branch:

```sh
git checkout -b feature/namn-på-funktionen
```

Om du redan har en branch och vill byta till den:

```sh
git checkout namn-på-branchen
```

### 2. **Kolla Status på Ditt Arbete**

Innan du gör något, kolla statusen på dina ändringar:

```sh
git status
```

Det visar vilka filer som har ändrats eller är i kö för commit.

### 3. **Lägga till Filer för Commit**

För att lägga till ändringar för commit:

```sh
git add filnamn  # Lägger till en specifik fil
git add .         # Lägger till alla ändrade filer
```

### 4. **Commit Changes**

Gör en commit för dina ändringar:

```sh
git commit -m "´Kort beskrivning av ändringarna"
```

### 5. **Pusha Din Branch till GitLab**

För att pusha din branch till remote (första gången):

```sh
git push origin feature/namn-på-funktionen
```

Det här skickar din **lokala branch** till **origin** (remote), så att andra kan se och arbeta med den.(Git kommer klaga om detta inte görs)
