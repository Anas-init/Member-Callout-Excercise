class LocalScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(local=self.request.user.local)
