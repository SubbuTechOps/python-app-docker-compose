# Dynamic Storage Provisioning with AWS EBS in Kubernetes

## Overview
Dynamic storage provisioning automates the creation of storage resources like AWS EBS volumes in Kubernetes. This document outlines the entire process, from enabling dynamic provisioning to testing the setup.

---

## Prerequisites
1. **Kubernetes Cluster**: Ensure you have a running EKS cluster.
   - Verify the cluster is accessible:
     ```bash
     kubectl get nodes
     ```
2. **AWS CLI**: Install and configure the AWS CLI with appropriate permissions.
   ```bash
   aws configure
   ```
3. **IAM Permissions**: Ensure your AWS account has the necessary IAM permissions to create EBS volumes and manage Kubernetes resources.

---

## Step 1: Enable the AWS EBS CSI Driver
1. **Install the EBS CSI Driver**:
   - Deploy the EBS CSI driver to the Kubernetes cluster:
     ```bash
     kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.38"
     ```

2. **Verify Installation**:
   - Check that the EBS CSI pods are running:
     ```bash
     kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver
     ```

---

## Step 2: Configure IAM Role for ServiceAccount
1. **Create an OIDC Provider**:
   - Confirm that an OIDC provider is associated with your cluster:
     ```bash
     aws eks describe-cluster --name <your-cluster-name> --query "cluster.identity.oidc.issuer"
     ```

2. **Create the IAM Role**:
   - Define a trust policy (`trust-policy.json`):
     ```json
     {
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Effect": "Allow",
                 "Principal": {
                     "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/<OIDC_PROVIDER_URL>"
                 },
                 "Action": "sts:AssumeRoleWithWebIdentity",
                 "Condition": {
                     "StringEquals": {
                         "<OIDC_PROVIDER_URL>:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa"
                     }
                 }
             }
         ]
     }
     ```
   - Create the IAM role:
     ```bash
     aws iam create-role --role-name AmazonEBSCSIDriverRole --assume-role-policy-document file://trust-policy.json
     ```

3. **Attach the Required Policy**:
   - Attach the `AmazonEBSCSIDriverPolicy` to the role:
     ```bash
     aws iam attach-role-policy --role-name AmazonEBSCSIDriverRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
     ```

4. **Annotate the ServiceAccount**:
   - Associate the role with the EBS CSI controller service account:
     ```bash
     kubectl annotate serviceaccount ebs-csi-controller-sa \
       eks.amazonaws.com/role-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:role/AmazonEBSCSIDriverRole \
       -n kube-system --overwrite
     ```

---

## Step 3: Create a StorageClass
Define a StorageClass to provision EBS volumes dynamically.

### Example: `storageclass.yaml`
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
```

Apply the StorageClass:
```bash
kubectl apply -f storageclass.yaml
```

Verify:
```bash
kubectl get sc
```

---

## Step 4: Create a PVC
Create a PersistentVolumeClaim (PVC) to request storage dynamically.

### Example: `test-pvc.yaml`
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-ebs-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: ebs-sc
```

Apply the PVC:
```bash
kubectl apply -f test-pvc.yaml
```

Verify the PVC status:
```bash
kubectl get pvc test-ebs-pvc
```

---

## Step 5: Attach the PVC to a Pod
Test the PVC by attaching it to a pod.

### Example: `test-pvc-pod.yaml`
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-ebs-pvc-pod
spec:
  containers:
    - name: busybox
      image: busybox
      command:
        - sh
        - -c
        - echo Test > /mnt/test && sleep 3600
      volumeMounts:
        - name: ebs-volume
          mountPath: /mnt
  volumes:
    - name: ebs-volume
      persistentVolumeClaim:
        claimName: test-ebs-pvc
```

Apply the Pod:
```bash
kubectl apply -f test-pvc-pod.yaml
```

Verify the pod status:
```bash
kubectl get pods test-ebs-pvc-pod
```

---

## Step 6: Validate the Setup
1. **Log into the Pod**:
   ```bash
   kubectl exec -it test-ebs-pvc-pod -- sh
   ```
2. **Check the Mounted Volume**:
   ```bash
   ls /mnt
   cat /mnt/test
   ```

Expected Output:
- A file named `test` with content `Test`.

---

## Step 7: Clean Up (Optional)
If this was a test:
- Delete the pod:
  ```bash
  kubectl delete pod test-ebs-pvc-pod
  ```
- Delete the PVC:
  ```bash
  kubectl delete pvc test-ebs-pvc
  ```

---

## Troubleshooting
- **PVC Pending**: Check the events for the PVC:
  ```bash
  kubectl describe pvc test-ebs-pvc
  ```
- **IAM Issues**: Verify the trust policy and attached policies for the IAM role.

---

## Summary
This document provides a step-by-step guide to enable dynamic storage provisioning using AWS EBS in Kubernetes. The setup includes installing the EBS CSI driver, configuring IAM roles, creating a StorageClass, and testing with a PVC and pod.

You can now confidently integrate this into your production workloads or CI/CD pipelines.


