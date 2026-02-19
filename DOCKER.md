## Docker Build

Base environment (from `biomni_env/environment.yml`):

```bash
docker build -t biomni:local .
```

Full E1 environment (runs `biomni_env/setup.sh`):

```bash
docker build -t biomni:local --build-arg BIOMNI_ENV=full .
```
