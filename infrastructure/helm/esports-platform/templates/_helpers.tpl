{{/*
Expand chart name.
*/}}
{{- define "esports-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name (release-chart, capped at 63 chars).
*/}}
{{- define "esports-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label: name-version
*/}}
{{- define "esports-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "esports-platform.labels" -}}
helm.sh/chart: {{ include "esports-platform.chart" . }}
{{ include "esports-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels — used in matchLabels and Services.
*/}}
{{- define "esports-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "esports-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Full image reference for a given service (api | frontend | worker).
Usage: include "esports-platform.image" (dict "root" . "service" "api")
*/}}
{{- define "esports-platform.image" -}}
{{- $root := .root }}
{{- $svc := .service }}
{{- $repo := index $root.Values $svc "image" "repository" }}
{{- printf "%s/%s/%s:%s" $root.Values.image.registry $root.Values.image.organization $repo $root.Values.image.tag }}
{{- end }}

{{/*
Name of the ExternalSecret-created Kubernetes Secret.
*/}}
{{- define "esports-platform.secretName" -}}
{{- printf "%s-secrets" (include "esports-platform.fullname" .) }}
{{- end }}

{{/*
Name of the app ConfigMap.
*/}}
{{- define "esports-platform.configMapName" -}}
{{- printf "%s-config" (include "esports-platform.fullname" .) }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "esports-platform.serviceAccountName" -}}
{{- printf "%s-sa" (include "esports-platform.fullname" .) }}
{{- end }}
