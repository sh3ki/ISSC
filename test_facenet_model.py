"""
Test if FaceNet model is working correctly
"""
import torch
from facenet_pytorch import InceptionResnetV1

print("=" * 60)
print("🧪 TESTING FACENET MODEL")
print("=" * 60)

# Initialize model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Device: {device}")

model = InceptionResnetV1(pretrained='vggface2').eval().to(device)
print("✅ Model initialized")

# Create 3 different random inputs
inputs = [
    torch.randn(1, 3, 160, 160).to(device),
    torch.randn(1, 3, 160, 160).to(device),
    torch.randn(1, 3, 160, 160).to(device)
]

outputs = []
with torch.no_grad():
    for i, x in enumerate(inputs):
        y = model(x).squeeze()
        outputs.append(y)
        print(f"\nInput #{i+1}:")
        print(f"   First 5: {y[:5].cpu().numpy()}")
        print(f"   Mean: {y.mean().item():.6f}, Std: {y.std().item():.6f}")

# Check if outputs are different
print("\n" + "=" * 60)
print("COMPARISON:")
print("=" * 60)
for i in range(len(outputs)):
    for j in range(i+1, len(outputs)):
        are_equal = torch.equal(outputs[i], outputs[j])
        distance = torch.dist(outputs[i], outputs[j]).item()
        print(f"Output {i+1} vs {j+1}: Equal={are_equal}, Distance={distance:.6f}")

if all(torch.dist(outputs[i], outputs[j]).item() > 0.1 for i in range(len(outputs)) for j in range(i+1, len(outputs))):
    print("\n✅ Model is working correctly - produces different outputs for different inputs")
else:
    print("\n❌ Model may be broken - outputs are too similar")

print("=" * 60)
