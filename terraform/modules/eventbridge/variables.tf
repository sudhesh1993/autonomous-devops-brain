variable "environment" {
     type = string 
}

variable "slack_webhook_url" { 
    type = string
    sensitive = true 
}