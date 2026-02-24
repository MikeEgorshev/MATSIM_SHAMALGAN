package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.NetworkWriter;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.misc.Time;
import org.matsim.pt.transitSchedule.api.Departure;
import org.matsim.pt.transitSchedule.api.TransitLine;
import org.matsim.pt.transitSchedule.api.TransitRoute;
import org.matsim.pt.transitSchedule.api.TransitRouteStop;
import org.matsim.pt.transitSchedule.api.TransitSchedule;
import org.matsim.pt.transitSchedule.api.TransitScheduleFactory;
import org.matsim.pt.transitSchedule.api.TransitScheduleWriter;
import org.matsim.pt.transitSchedule.api.TransitStopFacility;
import org.matsim.pt.utils.CreatePseudoNetwork;
import org.matsim.pt.utils.TransitScheduleValidator;
import org.matsim.vehicles.MatsimVehicleWriter;
import org.matsim.vehicles.Vehicle;
import org.matsim.vehicles.VehicleCapacity;
import org.matsim.vehicles.VehicleType;
import org.matsim.vehicles.VehicleUtils;
import org.matsim.vehicles.Vehicles;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Creates a simple PT supply from mapped OSM bus stops and assumptions.
 */
public class PrepareShamalganTransitFromAssumptions {

	private static final String TARGET_CRS = "EPSG:32643";
	private static final double DEFAULT_SPEED_KMH = 30.0;
	private static final double DEFAULT_DWELL_SEC = 60.0;
	// Rounded from MATSim examples mean headway (~366 sec).
	private static final int DEFAULT_HEADWAY_SEC = 360;
	private static final String DEFAULT_SERVICE_START = "06:00:00";
	private static final String DEFAULT_SERVICE_END = "23:00:00";

	private record StopSeed(String id, String name, double lon, double lat) {
	}

	private record MappedStop(String id, Coord coord) {
	}

	public static void main(String[] args) throws Exception {
		if (args.length < 5) {
			System.out.println("Usage:");
			System.out.println("  PrepareShamalganTransitFromAssumptions <input-network.xml> <bus-stops.csv> <output-network-with-pt.xml> <output-transitSchedule.xml> <output-transitVehicles.xml> [speedKmh] [dwellSec] [headwaySec] [serviceStart] [serviceEnd]");
			System.out.println("Example:");
			System.out.println("  PrepareShamalganTransitFromAssumptions scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00");
			return;
		}

		String inputNetwork = args[0];
		String stopsCsv = args[1];
		String outputNetworkWithPt = args[2];
		String outputTransitSchedule = args[3];
		String outputTransitVehicles = args[4];
		double speedKmh = args.length >= 6 ? Double.parseDouble(args[5]) : DEFAULT_SPEED_KMH;
		double dwellSec = args.length >= 7 ? Double.parseDouble(args[6]) : DEFAULT_DWELL_SEC;
		int headwaySec = args.length >= 8 ? Integer.parseInt(args[7]) : DEFAULT_HEADWAY_SEC;
		String serviceStart = args.length >= 9 ? args[8] : DEFAULT_SERVICE_START;
		String serviceEnd = args.length >= 10 ? args[9] : DEFAULT_SERVICE_END;

		if (!Files.exists(Path.of(inputNetwork))) {
			throw new IllegalArgumentException("Network file not found: " + Path.of(inputNetwork).toAbsolutePath());
		}
		if (!Files.exists(Path.of(stopsCsv))) {
			throw new IllegalArgumentException("Stops CSV not found: " + Path.of(stopsCsv).toAbsolutePath());
		}

		Config config = ConfigUtils.createConfig();
		config.global().setCoordinateSystem(TARGET_CRS);
		config.network().setInputFile(inputNetwork);
		config.transit().setUseTransit(true);
		Scenario scenario = ScenarioUtils.loadScenario(config);

		Network network = scenario.getNetwork();
		TransitSchedule schedule = scenario.getTransitSchedule();
		Vehicles transitVehicles = scenario.getTransitVehicles();
		TransitScheduleFactory f = schedule.getFactory();

		List<StopSeed> seeds = readStopsCsv(stopsCsv);
		if (seeds.size() < 2) {
			throw new IllegalStateException("Need at least 2 bus stops, found: " + seeds.size());
		}

		CoordinateTransformation tx = TransformationFactory.getCoordinateTransformation(
			TransformationFactory.WGS84,
			TARGET_CRS
		);
		List<MappedStop> mapped = mapStopsToNetwork(seeds, tx, network, f, schedule);
		List<MappedStop> ordered = orderByNearestNeighbor(mapped);

		double speedMps = speedKmh / 3.6;
		double serviceStartSec = Time.parseTime(serviceStart);
		double serviceEndSec = Time.parseTime(serviceEnd);
		if (!(serviceStartSec < serviceEndSec)) {
			throw new IllegalArgumentException("serviceStart must be before serviceEnd");
		}

		createVehicleType(transitVehicles, speedMps);
		TransitLine outbound = createLine(
			schedule, f, transitVehicles,
			"line_bus_assumed_outbound", "route_outbound",
			ordered, speedMps, dwellSec, serviceStartSec, serviceEndSec, headwaySec
		);
		TransitLine inbound = createLine(
			schedule, f, transitVehicles,
			"line_bus_assumed_inbound", "route_inbound",
			reversedCopy(ordered), speedMps, dwellSec, serviceStartSec, serviceEndSec, headwaySec
		);
		schedule.addTransitLine(outbound);
		schedule.addTransitLine(inbound);

		new CreatePseudoNetwork(schedule, network, "pt_", speedMps, 10000.0).createNetwork();

		var validation = TransitScheduleValidator.validateAll(schedule, network);
		if (!validation.isValid()) {
			System.out.println("Transit schedule validator reported issues:");
			TransitScheduleValidator.printResult(validation);
		}

		Path outNetwork = Path.of(outputNetworkWithPt);
		Path outSchedule = Path.of(outputTransitSchedule);
		Path outVehicles = Path.of(outputTransitVehicles);
		if (outNetwork.getParent() != null) Files.createDirectories(outNetwork.getParent());
		if (outSchedule.getParent() != null) Files.createDirectories(outSchedule.getParent());
		if (outVehicles.getParent() != null) Files.createDirectories(outVehicles.getParent());

		new NetworkWriter(network).write(outNetwork.toString());
		new TransitScheduleWriter(schedule).writeFile(outSchedule.toString());
		new MatsimVehicleWriter(transitVehicles).writeFile(outVehicles.toString());

		System.out.println("Assumed PT supply created.");
		System.out.println("Stops used: " + ordered.size());
		System.out.println("Headway sec: " + headwaySec + " ; service: " + serviceStart + " - " + serviceEnd);
		System.out.println("Speed km/h: " + speedKmh + " ; dwell sec: " + dwellSec);
		System.out.println("Network with PT: " + outNetwork.toAbsolutePath());
		System.out.println("Transit schedule: " + outSchedule.toAbsolutePath());
		System.out.println("Transit vehicles: " + outVehicles.toAbsolutePath());
	}

	private static List<StopSeed> readStopsCsv(String path) throws Exception {
		List<String> lines = Files.readAllLines(Path.of(path), StandardCharsets.UTF_8);
		if (lines.isEmpty()) return List.of();

		String[] header = lines.get(0).split(",", -1);
		int idxType = findColumn(header, "osm_type");
		int idxId = findColumn(header, "osm_id");
		int idxName = findColumn(header, "name");
		int idxLon = findColumn(header, "lon");
		int idxLat = findColumn(header, "lat");
		if (idxType < 0 || idxId < 0 || idxName < 0 || idxLon < 0 || idxLat < 0) {
			throw new IllegalArgumentException("Unexpected bus stop CSV header in " + path);
		}

		List<StopSeed> out = new ArrayList<>();
		for (int i = 1; i < lines.size(); i++) {
			String line = lines.get(i);
			if (line == null || line.isBlank()) continue;
			String[] p = line.split(",", -1);
			if (p.length <= Math.max(Math.max(idxLat, idxLon), idxName)) continue;
			String type = p[idxType].trim();
			String id = p[idxId].trim();
			String name = p[idxName].trim();
			double lon = Double.parseDouble(p[idxLon].trim());
			double lat = Double.parseDouble(p[idxLat].trim());
			String stopId = type + "_" + id;
			out.add(new StopSeed(stopId, name.isEmpty() ? stopId : name, lon, lat));
		}
		return out;
	}

	private static int findColumn(String[] header, String name) {
		for (int i = 0; i < header.length; i++) {
			if (name.equalsIgnoreCase(header[i].trim())) return i;
		}
		return -1;
	}

	private static List<MappedStop> mapStopsToNetwork(
		List<StopSeed> seeds,
		CoordinateTransformation tx,
		Network network,
		TransitScheduleFactory f,
		TransitSchedule schedule
	) {
		List<MappedStop> mapped = new ArrayList<>();
		for (StopSeed s : seeds) {
			Coord c = tx.transform(new Coord(s.lon, s.lat));
			Link link = org.matsim.core.network.NetworkUtils.getNearestLinkExactly(network, c);
			Id<TransitStopFacility> facId = Id.create("ptStop_" + s.id, TransitStopFacility.class);
			TransitStopFacility fac = f.createTransitStopFacility(facId, c, false);
			fac.setName(s.name);
			fac.setLinkId(link.getId());
			schedule.addStopFacility(fac);
			mapped.add(new MappedStop(s.id, c));
		}
		return mapped;
	}

	private static List<MappedStop> orderByNearestNeighbor(List<MappedStop> stops) {
		List<MappedStop> remaining = new ArrayList<>(stops);
		remaining.sort(Comparator.comparingDouble(s -> s.coord.getX()));
		List<MappedStop> ordered = new ArrayList<>();
		MappedStop current = remaining.remove(0);
		ordered.add(current);

		while (!remaining.isEmpty()) {
			MappedStop next = null;
			double best = Double.POSITIVE_INFINITY;
			for (MappedStop cand : remaining) {
				double d = dist(current.coord, cand.coord);
				if (d < best) {
					best = d;
					next = cand;
				}
			}
			ordered.add(next);
			remaining.remove(next);
			current = next;
		}
		return ordered;
	}

	private static List<MappedStop> reversedCopy(List<MappedStop> in) {
		List<MappedStop> out = new ArrayList<>();
		for (int i = in.size() - 1; i >= 0; i--) {
			out.add(in.get(i));
		}
		return out;
	}

	private static void createVehicleType(Vehicles vehicles, double speedMps) {
		Id<VehicleType> typeId = Id.create("busType_assumed", VehicleType.class);
		if (vehicles.getVehicleTypes().containsKey(typeId)) return;

		VehicleType type = VehicleUtils.createVehicleType(typeId);
		type.setMaximumVelocity(speedMps);
		type.setNetworkMode("pt");
		type.setLength(12.0);
		type.setPcuEquivalents(2.5);
		VehicleCapacity cap = type.getCapacity();
		cap.setSeats(35);
		cap.setStandingRoom(30);
		vehicles.addVehicleType(type);
	}

	private static TransitLine createLine(
		TransitSchedule schedule,
		TransitScheduleFactory f,
		Vehicles vehicles,
		String lineId,
		String routeId,
		List<MappedStop> ordered,
		double speedMps,
		double dwellSec,
		double serviceStartSec,
		double serviceEndSec,
		int headwaySec
	) {
		TransitLine line = f.createTransitLine(Id.create(lineId, TransitLine.class));
		List<TransitRouteStop> routeStops = new ArrayList<>();

		double offset = 0.0;
		for (int i = 0; i < ordered.size(); i++) {
			MappedStop ms = ordered.get(i);
			Id<TransitStopFacility> facId = Id.create("ptStop_" + ms.id, TransitStopFacility.class);
			TransitStopFacility fac = schedule.getFacilities().get(facId);
			double arrival = offset;
			double departure = offset + dwellSec;
			routeStops.add(f.createTransitRouteStop(fac, arrival, departure));
			if (i < ordered.size() - 1) {
				double runTime = dist(ms.coord, ordered.get(i + 1).coord) / speedMps;
				offset = departure + runTime;
			}
		}

		TransitRoute route = f.createTransitRoute(
			Id.create(routeId, TransitRoute.class),
			null,
			routeStops,
			"pt"
		);

		Id<VehicleType> typeId = Id.create("busType_assumed", VehicleType.class);
		int depCount = 0;
		for (double dep = serviceStartSec; dep <= serviceEndSec; dep += headwaySec) {
			Id<Departure> depId = Id.create(routeId + "_dep_" + depCount, Departure.class);
			Departure departure = f.createDeparture(depId, dep);
			Id<Vehicle> vehicleId = Id.createVehicleId(routeId + "_veh_" + depCount);
			Vehicle veh = VehicleUtils.createVehicle(vehicleId, vehicles.getVehicleTypes().get(typeId));
			vehicles.addVehicle(veh);
			departure.setVehicleId(vehicleId);
			route.addDeparture(departure);
			depCount++;
		}

		line.addRoute(route);
		return line;
	}

	private static double dist(Coord a, Coord b) {
		double dx = a.getX() - b.getX();
		double dy = a.getY() - b.getY();
		return Math.sqrt(dx * dx + dy * dy);
	}
}
