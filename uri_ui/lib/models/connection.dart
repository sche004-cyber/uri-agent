/// Authorization state of a connected external service.
enum ConnectionStatus { connected, needsAuthorization, notConnected }

/// A single external platform URI can be connected to.
///
/// This is a UI-side display model only. Real OAuth/API wiring is
/// explicitly out of scope for this prototype — see MockUriClient.
class ServiceConnection {
  const ServiceConnection({
    required this.id,
    required this.name,
    required this.description,
    required this.status,
    this.detail,
  });

  final String id;
  final String name;
  final String description;
  final ConnectionStatus status;
  final String? detail;

  ServiceConnection copyWith({ConnectionStatus? status, String? detail}) {
    return ServiceConnection(
      id: id,
      name: name,
      description: description,
      status: status ?? this.status,
      detail: detail ?? this.detail,
    );
  }
}
