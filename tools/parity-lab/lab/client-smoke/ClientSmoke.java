import com.google.gson.Gson;
import net.kyori.adventure.text.Component;
import org.geysermc.mcprotocollib.network.Session;
import org.geysermc.mcprotocollib.network.event.session.*;
import org.geysermc.mcprotocollib.network.factory.ClientNetworkSessionFactory;
import org.geysermc.mcprotocollib.network.packet.Packet;
import org.geysermc.mcprotocollib.protocol.MinecraftConstants;
import org.geysermc.mcprotocollib.protocol.MinecraftProtocol;
import org.geysermc.mcprotocollib.protocol.codec.MinecraftCodec;
import org.geysermc.mcprotocollib.protocol.packet.ingame.clientbound.entity.player.ClientboundPlayerPositionPacket;
import org.geysermc.mcprotocollib.protocol.packet.ingame.serverbound.level.ServerboundAcceptTeleportationPacket;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Offline login/configuration/play-entry smoke. No credentials, chat or movement. */
public class ClientSmoke {
    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(args[0]);
        Path output = Path.of(args[1]);
        if (port < 1 || port > 65535 || MinecraftCodec.CODEC.getProtocolVersion() != 777
                || !MinecraftCodec.CODEC.getMinecraftVersion().equals("26.3")) {
            throw new IllegalArgumentException("Requires exact 26.3 / protocol 777 and a loopback game port");
        }
        var events = Collections.synchronizedList(new ArrayList<Map<String, Object>>());
        var seen = java.util.concurrent.ConcurrentHashMap.<String>newKeySet();
        var finished = new CountDownLatch(1);
        var result = new java.util.concurrent.ConcurrentHashMap<String, Object>();
        result.put("coverage", "offline-login-configuration-play-entry");
        result.put("gameplay_tested", false);
        result.put("status", "error");
        result.put("protocol", 777);
        result.put("version", "26.3");
        var client = ClientNetworkSessionFactory.factory().setAddress("127.0.0.1", port)
                .setProtocol(new MinecraftProtocol("ParitySmoke")).create();
        client.setFlag(MinecraftConstants.FOLLOW_TRANSFERS, false);
        client.addListener(new SessionAdapter() {
            private void record(String direction, Packet packet) {
                String name = packet.getClass().getSimpleName();
                seen.add(direction + ":" + name);
                if (events.size() < 4096) {
                    events.add(Map.of("at", Instant.now().toString(), "direction", direction, "packet", name));
                } else {
                    result.put("event_limit_exceeded", true);
                    client.disconnect(Component.text("Smoke event limit exceeded"));
                }
            }
            @Override public void packetReceived(Session session, Packet packet) {
                record("received", packet);
                if (packet instanceof ClientboundPlayerPositionPacket position) {
                    result.put("initial_position", position.getPosition().toString());
                    if (!position.getRelatives().isEmpty()) {
                        result.put("unsupported_relative_position", position.getRelatives().toString());
                        session.disconnect(Component.text("Relative initial position unsupported by smoke client"));
                        return;
                    }
                    session.send(new ServerboundAcceptTeleportationPacket(position.getId(),
                            position.getPosition().getX(), position.getPosition().getY(), position.getPosition().getZ(),
                            position.getYRot(), position.getXRot()));
                }
            }
            @Override public void packetSent(Session session, Packet packet) {
                record("sent", packet);
            }
            @Override public void disconnected(DisconnectedEvent event) {
                result.put("disconnect_reason", event.getReason().toString());
                if (event.getCause() != null) result.put("disconnect_cause", event.getCause().toString());
                finished.countDown();
            }
        });
        try {
            client.connect(false);
            // A pass requires decoded login/configuration/play packets AND acknowledgments.
            Set<String> required = Set.of("received:ClientboundLoginFinishedPacket",
                    "received:ClientboundFinishConfigurationPacket", "received:ClientboundLoginPacket",
                    "received:ClientboundPlayerPositionPacket", "sent:ServerboundLoginAcknowledgedPacket",
                    "sent:ServerboundFinishConfigurationPacket", "sent:ServerboundAcceptTeleportationPacket");
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(20);
            while (!seen.containsAll(required) && finished.getCount() != 0 && System.nanoTime() < deadline) {
                finished.await(50, TimeUnit.MILLISECONDS);
            }
            if (seen.containsAll(required) && finished.getCount() != 0) {
                // Retain packet decoding / disconnect failures arriving just after play entry.
                if (!finished.await(2, TimeUnit.SECONDS) && client.isConnected()
                        && !result.containsKey("event_limit_exceeded")) result.put("status", "pass");
            }
            result.put("required_packets", required.stream().sorted().toList());
            result.put("seen", seen.stream().sorted().toList());
        } catch (Throwable failure) {
            result.put("exception", failure.toString());
        } finally {
            client.disconnect(Component.text("Bounded parity smoke finished"));
            finished.await(2, TimeUnit.SECONDS);
            synchronized (events) { result.put("events", new ArrayList<>(events)); }
            Files.writeString(output, new Gson().toJson(result) + "\n");
        }
        // MCProtocolLib's shared Netty event loop can outlive the disconnected session.
        System.exit(result.get("status").equals("pass") ? 0 : 2);
    }
}
