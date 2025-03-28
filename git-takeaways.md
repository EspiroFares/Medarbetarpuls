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

Eller

```sh
git switch namn-på-branchen
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

### **När måste du använda `origin`?**
- **Första gången du pushar en branch till remote**:
  När du skapar en ny branch lokalt och vill dela den med alla  genom att ladda upp den till **remote** repositoryt, använder du `origin`:
  ```sh
  git push origin feature/namn-på-funktionen
  ```
- **För att hämta ändringar från remote och slå samman dem (om du inte har kopplat din lokala branch med remote)**:
  Om du vill hämta de senaste ändringarna från remote och uppdatera din lokala branch, måste du ofta specificera `origin` för att Git ska veta vilken remote du refererar till:
  ```sh
  git pull origin main
  ```

  ### 6. **Pull för Att Hämta de Nyaste Ändringarna**
Innan du börjar jobba på din branch, se till att hämta de senaste ändringarna från remote:
```sh
git pull     #updaterar den branchen du står på
```
Detta uppdaterar din lokala branch med alla ändringar som har gjorts på den branchen sedan du sist hämtade.
(viktigt att du först har kopplat din lokala branch till remove med `origin`)

### 7. **Merge en Branch**
När du har slutfört ditt arbete och vill mergea din branch med `dev`:
git checkout dev
git pull origin dev  # För att vara säker på att du har den senaste versionen (origin för att säkerställa att det är remote behövs egentligen inte)
git merge feature/namn-på-funktionen

### 8. **Rensa Upp Efter Merge**
När din branch är mergad, kan du ta bort den både lokalt och på remote (så vi slipper onödiga branches):
git branch -d feature/namn-på-funktionen   # Lokalt
git push origin --delete feature/namn-på-funktionen   # Remote

### 9. **Hantera Merge-konflikter**
Om du får merge-konflikter när du försöker merga, öppna de berörda filerna och lös konflikten(alternativt säg till mig:) ). Efter att du löst konflikten, använd:
git add filnamn  # Lägger till lösningen för konflikterna
git commit       # Skapar en commit för lösningen

