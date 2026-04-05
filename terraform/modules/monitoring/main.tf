resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
  }
}

resource "helm_release" "prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "58.1.0"
  namespace  = kubernetes_namespace.monitoring.metadata
  timeout    = 600

  values = [
    file("${path.module}/alertmanager-values.yaml")
  ]
}values = [
    file("${path.module}/alertmanager-values.yaml")
  ]
}

  set {
    name  = "grafana.adminPassword"
    value = var.grafana_password
  }

  set {
    name  = "grafana.service.type"
    value = "LoadBalancer"
  }

  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "7d"
  }

  set {
    name  = "prometheus.prometheusSpec.resources.requests.memory"
    value = "512Mi"
  }

  set {
    name  = "prometheus.prometheusSpec.resources.limits.memory"
    value = "1Gi"
  }

  # Reduce resource usage for dev
  set {
    name  = "alertmanager.alertmanagerSpec.resources.requests.memory"
    value = "128Mi"
  }
}