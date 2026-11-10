# __NAME__

A Go API in `apps/api` and a Vue app in `apps/app`, deployed with Kamal; `.about/adr/stack.md`
says why each choice was made.

## Needs

git, mise and Docker; mise installs every other tool at the version `mise.toml` pins.

## Start

```sh
mise trust && mise run setup
mise run dev
```

`mise run setup` installs the tools and turns the Git hooks on in this clone. `mise run dev` starts
Postgres in Docker on port 5433, runs the API on <http://localhost:8080>, migrating the database
first, and serves the app on <http://localhost:5173>, which passes `/api` on to the API. Ctrl-C
stops the API and the app; `docker compose down` stops Postgres.

`mise run check` is what CI runs: run it before you push.

## Publish

Create the GitHub repo and push to it, with `gh`:

```sh
gh repo create __OWNER__/__NAME__ --private --source . --push
```

## Deploy

Kamal deploys the image of the `Dockerfile` to one server you own, behind kamal-proxy, with
Postgres beside it. Before the first deploy:

1. Replace the example migration and query, `apps/api/migrations/00001_notes.sql` and
   `apps/api/queries/notes.sql`, with the product's first real ones, then `mise run sqlc`.
2. In `config/deploy.yml`, replace `<server>`, both times, with the server's IP address or host
   name, which Kamal reaches over SSH as root with your SSH agent's key, and `<registry>` with the
   registry the image goes to, such as `ghcr.io`.
3. Copy `.env.example` to `.env`, which is never committed, and fill in each secret it names.
4. Set the server up and deploy:

   ```sh
   mise run deploy setup
   ```

After that, each deploy is `mise run deploy`; `mise run deploy <command>` runs any other Kamal
command, such as `mise run deploy app logs`. The app answers on the server's address over HTTP;
once a domain points at the server, add `host:` with the domain and `ssl: true` under `proxy:`
in `config/deploy.yml` and deploy again.
