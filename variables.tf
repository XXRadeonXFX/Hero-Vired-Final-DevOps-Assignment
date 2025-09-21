variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "vpc_id" {
  description = "Existing VPC ID"
  type        = string
  default     = "vpc-0056d809452f9f8ea"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "flask-app-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27"
}

variable "ecr_repository_name" {
  description = "ECR repository name for Flask app"
  type        = string
  default     = "flask-app"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS nodes"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of nodes"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of nodes"
  type        = number
  default     = 4
}

variable "node_min_size" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "workstation_cidr" {
  description = "CIDR block for workstation access"
  type        = string
  default     = "0.0.0.0/0" # Restrict this to your IP in production
}

variable "key_pair_name" {
  description = "EC2 Key Pair name for node access"
  type        = string
  default     = "my-key-pair" # Change this to your key pair
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "flask-app-eks"
    Owner       = "devops-team"
  }
}