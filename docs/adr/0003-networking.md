# ADR 0003: No-NAT demonstration network

Status: Accepted with live validation pending

Run Fargate tasks in public subnets with public egress and accept traffic only from the HTTPS load
balancer security group. Keep RDS in isolated subnets. This removes NAT gateway cost. Task public IPs
are not application entry points because the task security group permits port 8000 only from the ALB.

