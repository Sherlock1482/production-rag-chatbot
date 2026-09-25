from utils.candidate_resolver import resolve_candidate


candidate = resolve_candidate("Rajuu Sharma")

print("\nResolved candidate:\n")

if candidate:
    print("Candidate:", candidate["candidate_name"])
    print("Email:", candidate["email"])
    print("Source:", candidate["source"])
else:
    print("Candidate not found.")