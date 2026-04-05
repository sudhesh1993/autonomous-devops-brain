variable "environment" {
     type = string 
}

variable "slack_webhook_url" { 
    type = string
    sensitive = true 
}

variable "oidc_provider_arn" { 
    type = string 
}

variable "oidc_issuer" { 
    type = string 
}