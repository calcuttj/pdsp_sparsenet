import numpy as np
from math import ceil, sqrt, exp, pi
import h5py as h5
import multiprocessing as mp

class PlaneData:
  def __init__(self, wire, time, integral):
    self.wire = wire
    self.time = time
    self.integral = integral

class PDSPData:
  def __init__(self, maxtime=913, linked=True, maxwires=[800, 800, 480]):
    self.maxtime=maxtime
    self.maxwires=maxwires
    self.linked = linked
    self.tp = np.dtype([('integral', 'f4'),
                        ('rms', 'f4'), ('time', 'f4'), ('wire', 'f4')])

  def get_plane_data(self, h5in, k, eid, pid):
    ##To-Do: check maxtime and wires
    #events = np.array(h5in[f'{k}/events/event_id'][:])
    hit_events = np.array(h5in[f'{k}/plane_{pid}_hits/event_id'][:])
    #print(hit_events)
    #print(eid)
    indices = np.all(hit_events == eid, axis=1)
    #print(np.array(h5in[f'{k}/plane_{pid}_hits']['wire'])[indices].flatten().astype(int))
    plane_data = PlaneData(
               np.array(h5in[f'{k}/plane_{pid}_hits']['wire'][:])[indices].flatten().astype(int),
               (912 - (np.array(h5in[f'{k}/plane_{pid}_hits']['time'][:])[indices]- 500.)/6.025).flatten().astype(int),
               np.array(h5in[f'{k}/plane_{pid}_hits']['integral'][:])[indices].flatten()
           )
    #to_del = np.where((plane_data.time >= self.maxtime) |
    #                  (plane_data.wire >= self.maxwires[pid]))

    #print('Wire', pid, plane_data.wire)
    #print('Time', pid, plane_data.time)
    #print('ToD', pid, to_del)
    #plane_data.time = np.delete(plane_data.time, to_del)
    #plane_data.wire = np.delete(plane_data.wire, to_del)
    #plane_data.integral = np.delete(plane_data.integral, to_del)
    return plane_data


  def load_file_mp(self, h5in, procid):
    ### Getting truth
    #pdg = [] 
    #interacted = []
    #n_neutron = []
    #n_proton = []
    #n_piplus = []
    #n_piminus = []
    #n_pi0 = []

    for a, k in enumerate(self.split_keys[procid]):

      events = [i for i in np.array(h5in[f'{k}/events/event_id'][:])]

      if not a % 100:
        with self.lock:
          string = ''
          self.split_count[procid] = a
          for i in range(len(self.split_count)):
            string += f'{self.split_count[i]}/{len(self.split_keys[i])} '
          #print(f'{procid}: {a}/{len(self.split_keys[procid])}'), end='\r')
          print(string, end='\r')
          #print(string, end='\x1b[1K\r')

      all_plane_datas = []
      for eid in events:
        all_plane_datas.append(
          [self.get_plane_data(h5in, k, eid, i) for i in range(3)])
      #nhits = [i for i in np.array(h5in[f'{k}/events/nhits'][:])]
      nhits = np.array(h5in[f'{k}/events/nhits'])
      #print('nhits:', nhits)

      pdg = [i[0] for i in np.array(h5in[f'{k}/truth/pdg'])]
      interacted = [i[0] for i in np.array(h5in[f'{k}/truth/interacted'])]
      n_neutron = [i[0] for i in np.array(h5in[f'{k}/truth/n_neutron'])]
      n_proton = [i[0] for i in np.array(h5in[f'{k}/truth/n_proton'])]
      n_piplus = [i[0] for i in np.array(h5in[f'{k}/truth/n_piplus'])]
      n_piminus = [i[0] for i in np.array(h5in[f'{k}/truth/n_piminus'])]
      n_pi0 = [i[0] for i in np.array(h5in[f'{k}/truth/n_pi0'])]

      topos = []
      for i in range(len(pdg)):
        if pdg[i] not in [211, -13]:
          topos.append(-1)
        elif not interacted[i]:
          topos.append(3)
        elif (n_piplus[i] == 0 and n_piminus[i] == 0 and
              n_pi0[i] == 0):
          topos.append(0)
        elif (n_piplus[i] == 0 and n_piminus[i] == 0 and
              n_pi0[i] == 1):
          topos.append(1)
        else:
          topos.append(2)
      #print(f'Added {len(sub_pdg)} truths from {k}')

      with self.lock:
        #print(len(nhits), len(pdg), len(all_plane_datas), len(events))
        for plane_data in all_plane_datas:
          self.plane2_time.append(plane_data[2].time)
          self.plane2_wire.append(plane_data[2].wire)
          self.plane2_integral.append(plane_data[2].integral)

          self.plane1_time.append(plane_data[1].time)
          self.plane1_wire.append(plane_data[1].wire)
          self.plane1_integral.append(plane_data[1].integral)

          self.plane0_time.append(plane_data[0].time)
          self.plane0_wire.append(plane_data[0].wire)
          self.plane0_integral.append(plane_data[0].integral)
        #for eid in events: self.events.append(eid)
        #for n in nhits: self.nhits.append(n)
        for i in range(len(pdg)):
          self.nhits.append(nhits[i])
          self.events.append(events[i])
          self.pdg.append(pdg[i])
          self.interacted.append(interacted[i])
          self.n_neutron.append(n_neutron[i])
          self.n_proton.append(n_proton[i])
          self.n_piplus.append(n_piplus[i])
          self.n_piminus.append(n_piminus[i])
          self.n_pi0.append(n_pi0[i])
          self.topos.append(topos[i])

  def load_h5_mp(self, filename, num_workers):
    with h5.File(filename, 'r') as h5in:
      self.loaded_truth = False

      ##Make lock and manager
      ##And associated lists
      with mp.Manager() as manager:
        self.lock = mp.Lock()
        self.events = manager.list() 
        self.plane0_time = manager.list()
        self.plane0_wire = manager.list()
        self.plane0_integral = manager.list()

        self.plane1_time = manager.list()
        self.plane1_wire = manager.list()
        self.plane1_integral = manager.list()

        self.plane2_time = manager.list()
        self.plane2_wire = manager.list()
        self.plane2_integral = manager.list()

        self.pdg = manager.list()
        self.interacted = manager.list()
        self.n_proton = manager.list()
        self.n_neutron = manager.list()
        self.n_piplus = manager.list()
        self.n_piminus = manager.list()
        self.n_pi0 = manager.list()
        self.topos = manager.list()


        self.keys = [k for k in h5in.keys()]
        self.split_keys = manager.list([
          self.keys[i::num_workers]
          for i in range(num_workers)
        ])

        self.split_count = manager.list([0 for i in range(num_workers)])

        self.nhits = manager.list() 

        procs = [
          mp.Process(target=self.load_file_mp,
                     args=(h5in, i))
          for i in range(num_workers)
        ]

        for p in procs:
          p.start()
        for p in procs:
          p.join()

        self.plane0_time = list(self.plane0_time) 
        self.plane0_wire = list(self.plane0_wire)
        self.plane0_integral = list(self.plane0_integral)

        self.plane1_time = list(self.plane1_time) 
        self.plane1_wire = list(self.plane1_wire)
        self.plane1_integral = list(self.plane1_integral)

        self.plane2_time = list(self.plane2_time) 
        self.plane2_wire = list(self.plane2_wire)
        self.plane2_integral = list(self.plane2_integral)

        self.wires = [self.plane0_wire, self.plane1_wire, self.plane2_wire]
        self.times = [self.plane0_time, self.plane1_time, self.plane2_time]
        self.integrals = [self.plane0_integral, self.plane1_integral, self.plane2_integral]
        self.nhits = np.array(self.nhits)

        self.nevents = len(self.nhits)
        self.events = np.array(self.events)

        print(f'Loading truth')
        self.pdg = np.array(self.pdg)
        self.interacted = np.array(self.interacted)
        self.n_proton = np.array(self.n_proton)
        self.n_neutron = np.array(self.n_neutron)
        self.n_piplus = np.array(self.n_piplus)
        self.n_piminus = np.array(self.n_piminus)
        self.n_pi0 = np.array(self.n_pi0)
        self.topos = np.array(self.topos)

        #self.load_truth(h5in)


  def load_h5(self, filename):
    with h5.File(filename, 'r') as h5in:

      self.loaded_truth = False
      self.plane0_time = []
      self.plane0_wire = []
      self.plane0_integral = []

      self.plane1_time = []
      self.plane1_wire = []
      self.plane1_integral = []

      self.plane2_time = []
      self.plane2_wire = []
      self.plane2_integral = []

      self.keys = [k for k in h5in.keys()]
      nhits = []

      self.events = []
      for a, k in enumerate(self.keys):
        nhits += [i for i in np.array(h5in[f'{k}/events/nhits'][:])]

        temp_events = [i for i in np.array(h5in[f'{k}/events/event_id'][:])]
        self.events += temp_events

        if not a % 100: print(f'{a}/{len(self.keys)}', end='\r')
        for eid in temp_events:
          #plane_data = self.get_plane_data(h5in, k, eid, 0)
          #self.plane0_time.append(plane_data.time)
          #self.plane0_wire.append(plane_data.wire)
          #self.plane0_integral.append(plane_data.integral)

          #plane_data = self.get_plane_data(h5in, k, eid, 1)
          #self.plane1_time.append(plane_data.time)
          #self.plane1_wire.append(plane_data.wire)
          #self.plane1_integral.append(plane_data.integral)

          plane_data = self.get_plane_data(h5in, k, eid, 2)
          self.plane2_time.append(plane_data.time)
          self.plane2_wire.append(plane_data.wire)
          self.plane2_integral.append(plane_data.integral)

      self.wires = [self.plane0_wire, self.plane1_wire, self.plane2_wire]
      self.times = [self.plane0_time, self.plane1_time, self.plane2_time]
      self.integrals = [self.plane0_integral, self.plane1_integral, self.plane2_integral]
      self.nhits = np.array(nhits)
      self.events = np.array(self.events)

      self.nevents = len(self.nhits)

      print(f'Loading truth')
      self.load_truth(h5in)
      #self.clean_events()
      #print('getting event')
      #if self.nevents > 0:
      #  self.get_event(0)

  def get_indices(self, pdg):
    return [i for i in range(len(self.pdg)) if self.pdg[i][0] == pdg]

  def load_truth(self, h5in):
    if self.loaded_truth:
      print('Already loaded truth info')
      return
    self.loaded_truth = True
    if not self.linked:
      if 'truth' in h5in.keys():
        found_truth = True
        self.pdg = np.array(h5in['truth']['pdg'][:]) 
        self.interacted = np.array(h5in['truth']['interacted'][:])
        self.n_neutron = np.array(h5in['truth']['n_neutron'][:])
        self.n_proton = np.array(h5in['truth']['n_proton'][:])
        self.n_piplus = np.array(h5in['truth']['n_piplus'][:])
        self.n_piminus = np.array(h5in['truth']['n_piminus'][:])
        self.n_pi0 = np.array(h5in['truth']['n_pi0'][:])

        self.pdg = np.ndarray.flatten(self.pdg)
        self.interacted = np.ndarray.flatten(self.interacted)
        self.n_neutron = np.ndarray.flatten(self.n_neutron)
        self.n_proton = np.ndarray.flatten(self.n_proton)
        self.n_piplus = np.ndarray.flatten(self.n_piplus)
        self.n_piminus = np.ndarray.flatten(self.n_piminus)
        self.n_pi0 = np.ndarray.flatten(self.n_pi0)

    else:
      found_truth = False 
      pdg = [] 
      interacted = []
      n_neutron = []
      n_proton = []
      n_piplus = []
      n_piminus = []
      n_pi0 = []
      for k in self.keys:
        if 'truth' in h5in[f'{k}'].keys():
          found_truth = True

          sub_pdg = [i for i in np.array(h5in[f'{k}/truth/pdg'][:])]

          pdg += sub_pdg
          interacted += [i for i in np.array(h5in[f'{k}/truth/interacted'][:])]
          n_neutron += [i for i in np.array(h5in[f'{k}/truth/n_neutron'][:])]
          n_proton += [i for i in np.array(h5in[f'{k}/truth/n_proton'][:])]
          n_piplus += [i for i in np.array(h5in[f'{k}/truth/n_piplus'][:])]
          n_piminus += [i for i in np.array(h5in[f'{k}/truth/n_piminus'][:])]
          n_pi0 += [i for i in np.array(h5in[f'{k}/truth/n_pi0'][:])]

          #print(f'Added {len(sub_pdg)} truths from {k}')

      if found_truth:
        self.pdg = np.array(pdg)
        self.interacted = np.array(interacted)
        self.n_proton = np.array(n_proton)
        self.n_neutron = np.array(n_neutron)
        self.n_piplus = np.array(n_piplus)
        self.n_piminus = np.array(n_piminus)
        self.n_pi0 = np.array(n_pi0)

        self.pdg = np.ndarray.flatten(self.pdg)
        self.interacted = np.ndarray.flatten(self.interacted)
        self.n_neutron = np.ndarray.flatten(self.n_neutron)
        self.n_proton = np.ndarray.flatten(self.n_proton)
        self.n_piplus = np.ndarray.flatten(self.n_piplus)
        self.n_piminus = np.ndarray.flatten(self.n_piminus)
        self.n_pi0 = np.ndarray.flatten(self.n_pi0)

    if found_truth: self.get_truth_topos()

  def get_truth_topos(self):
    topos = []
    for i in range(len(self.pdg)):
      if self.pdg[i] not in [211, -13]:
        topos.append(-1)
      elif not self.interacted[i]:
        topos.append(3)
      elif (self.n_piplus[i] == 0 and self.n_piminus[i] == 0 and
            self.n_pi0[i] == 0):
        topos.append(0)
      elif (self.n_piplus[i] == 0 and self.n_piminus[i] == 0 and
            self.n_pi0[i] == 1):
        topos.append(1)
      else:
        topos.append(2)
    self.topos = np.array(topos)

  def load_data(self, pid, eventindex):  #TODO remove

    data = np.zeros(self.nhits[eventindex][pid], dtype=self.tp)

    if self.linked:
      key = self.event_keys[eventindex]
      indices = [np.all(i) for i in self.hit_events[pid][key] == self.events[eventindex]]

    key = '' if not self.linked else f'{key}/'

    for n in self.tp.names:
      if n == 'event_id':
        data[n] = self.data[f'{key}{n}'][pid][indices]
      else:
        data[n] = self.data[f'{key}{n}'][pid][indices].reshape(self.nhits[eventindex][pid])
    return data

  def get_plane(self, eventindex, pid):
    #check eventindex
    if pid not in [0, 1, 2]:
      ##TODO -- throw exception
      return 0

    nhits = self.nhits[eventindex, pid]
    locations = np.zeros((nhits, 2), dtype=int)
    locations[:, 0] = self.wires[pid][eventindex]
    locations[:, 1] = self.times[pid][eventindex]
    #locations[:, 2] = np.arange(nhits)

    features = np.array([[i] for i in self.integrals[pid][eventindex]])
    return (locations, features)


    


  def make_plane(self, eventindex, pid=2, pad2=False):
    plane = np.zeros((480 if (pid == 2 and not pad2) else 800, self.maxtime))

    if pid not in [0, 1, 2]:
      ##TODO -- throw exception
      return 0


    wires = self.wires[pid][eventindex]
    times = self.times[pid][eventindex]

    for i in range(len(wires)):
      plane[wires[i], times[i]] = self.integrals[pid][eventindex][i]


    return plane


  def clean_events(self, check_nhits=True):
  ##Check this -- not working
    nohits = np.any(self.nhits == 0, axis=1)
    print(len(nohits))
    indices = np.where(
      ((self.pdg != 211) & (self.pdg != -13)) |
      (nohits if check_nhits else check_nhits)
    )

    self.pdg = np.delete(self.pdg, indices)
    self.topos = np.delete(self.topos, indices)
    self.interacted = np.delete(self.interacted, indices)
    self.n_neutron = np.delete(self.n_neutron, indices)
    self.n_proton = np.delete(self.n_proton, indices)
    self.n_piplus = np.delete(self.n_piplus, indices)
    self.n_piminus = np.delete(self.n_piminus, indices)
    self.n_pi0 = np.delete(self.n_pi0, indices)
    self.events = np.delete(self.events, indices)

    #self.events = np.delete(self.events, indices, axis=0)
    self.nhits = np.delete(self.nhits, indices, axis=0)
    #self.event_keys = np.delete(self.event_keys, indices)
    self.nevents -= len(indices[0])

    for i in indices[0][::-1]:
      #print('Deleting', i)
      self.delete_event(i)

  def delete_event(self, i):
    del self.plane0_time[i]
    del self.plane0_wire[i]
    del self.plane0_integral[i]

    del self.plane1_time[i]
    del self.plane1_wire[i]
    del self.plane1_integral[i]

    del self.plane2_time[i]
    del self.plane2_wire[i]
    del self.plane2_integral[i]

  def get_nbatches(self, batchsize=2):
    return ceil(self.nevents/batchsize)

  def get_sample_weights(self):
    return 1./np.array([self.topos[self.topos == i].size for i in range(4)])

  def get_training_batches(self, batchsize=2, maxbatches=-1, startbatch=0):

    for i in range(startbatch, ceil(self.nevents/batchsize)):
      if maxbatches > 0 and i > maxbatches: break
      print('Batch', i)
      #print('\t', np.arange(self.nevents)[i*batchsize:(i+1)*batchsize])

      batch_events = np.arange(self.nevents)[i*batchsize:(i+1)*batchsize]
      nb = len(batch_events)
      #plane_batch = np.zeros((nb, 1, ))
      nhits = int(sum(self.nhits[i*batchsize:(i+1)*batchsize, 2]))
      locs_batch = np.zeros((nhits, 3), dtype=int)
      features_batch = np.zeros((nhits, 1))

      truth_batch = np.zeros((nb, 4))
      start = 0
      for a, j in enumerate(batch_events):
        #print(j)
        locations, features = self.get_plane(j, 2)
        locs_batch[start:start+len(locations), :2] = locations
        locs_batch[start:start+len(locations), 2] = a
        features_batch[start:start+len(locations)] = features
        start += len(locations)

        truth_batch[a, self.topos[j]] = 1.

      yield ((locs_batch, features_batch), truth_batch)
