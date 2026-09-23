"""Durable, source-linked analytical snapshots for the single workshop."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AnalyticsSnapshot(models.Model):
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="analytics_snapshots")
    trigger = models.CharField(max_length=32, default="manual")
    source_fingerprint = models.CharField(max_length=64)
    audit_cursor = models.BigIntegerField(default=0)
    source_counts = models.JSONField(default=dict)
    freshness = models.JSONField(default=dict)
    source_refs = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)

    class Meta:
        ordering = ["-recorded_at", "-pk"]


class AnalyticsRow(models.Model):
    snapshot = models.ForeignKey(AnalyticsSnapshot, on_delete=models.CASCADE, related_name="rows")
    mart = models.CharField(max_length=40, db_index=True)
    key = models.CharField(max_length=160)
    data = models.JSONField(default=dict)

    class Meta:
        ordering = ["mart", "key", "pk"]
        constraints = [models.UniqueConstraint(fields=["snapshot", "mart", "key"], name="uniq_analytics_snapshot_mart_key")]
        indexes = [models.Index(fields=["snapshot", "mart"])]
