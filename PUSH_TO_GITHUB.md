# Push this project to your GitHub fork

This repo already has **origin** set (e.g. to `ligfx/datahub-data-access-workflow-examples`). To push to **your** fork:

## 1. Create your fork on GitHub

- Go to the current origin repo on GitHub and click **Fork** (top right), or create a new repo under your account with the same name.
- Copy your fork’s URL: `https://github.com/YOUR_USERNAME/datahub-data-access-workflow-examples.git`

## 2. Add your fork as a remote and push

From the project root:

```bash
cd datahub-data-access-workflow-examples

# Add your fork (use a different name so origin stays as upstream)
git remote add myfork https://github.com/YOUR_USERNAME/datahub-data-access-workflow-examples.git
# Or with SSH: git remote add myfork git@github.com:YOUR_USERNAME/datahub-data-access-workflow-examples.git

# Commit your current changes (if any)
git add .
git status   # confirm .env is not listed
git commit -m "Your commit message"

# Push to your fork
git push -u myfork main
```

Replace `YOUR_USERNAME` with your GitHub username. If your default branch is `master` instead of `main`, use `git push -u myfork master`.

## 3. Optional: Make your fork the default remote

If you’ll usually push to your fork and only sometimes pull from the original:

```bash
git remote rename origin upstream
git remote rename myfork origin
git push -u origin main
```

Then `git push` / `git pull` use your fork; pull from upstream with `git fetch upstream && git merge upstream/main`.

## 4. Confirm

- Open `https://github.com/YOUR_USERNAME/datahub-data-access-workflow-examples` and confirm files and history look right.
- Ensure **.env is not in the repo** (it’s in .gitignore). Run `git status` before committing; if .env ever appeared as tracked, remove it and rotate the token.
